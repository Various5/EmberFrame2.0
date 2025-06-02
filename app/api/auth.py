# app/api/auth_advanced.py
"""
Advanced Authentication Features - 2FA, Password Reset, Session Management
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
import pyotp
import qrcode
import io
import base64
from datetime import datetime, timedelta

from app.core.dependencies import get_db, get_current_user
from app.core.security import (
    verify_password, get_password_hash, create_access_token, 
    create_refresh_token, verify_refresh_token, auth_security,
    validate_password_strength
)
from app.models.user import User, Session as UserSession, SessionStatus
from app.schemas.auth_advanced import (
    TwoFactorSetupResponse, TwoFactorVerifyRequest, PasswordResetRequest,
    PasswordResetConfirm, PasswordChangeRequest, SessionResponse,
    SecuritySettingsResponse, SecuritySettingsUpdate
)
from app.services.email_service import EmailService
from app.services.audit_service import AuditService
from app.utils.helpers import get_client_ip, generate_random_string

auth_advanced_router = APIRouter()

@auth_advanced_router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
async def setup_two_factor(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Setup two-factor authentication"""
    if current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is already enabled"
        )

    # Generate secret
    secret = pyotp.random_base32()
    
    # Create TOTP instance
    totp = pyotp.TOTP(secret)
    
    # Generate QR code
    provisioning_uri = totp.provisioning_uri(
        name=current_user.email or current_user.username,
        issuer_name="EmberFrame V2"
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_str = base64.b64encode(img_buffer.getvalue()).decode()
    
    # Store secret temporarily (will be confirmed on verification)
    current_user.two_factor_secret = secret
    db.commit()
    
    return TwoFactorSetupResponse(
        secret=secret,
        qr_code=f"data:image/png;base64,{img_str}",
        backup_codes=[]  # Generate backup codes after verification
    )

@auth_advanced_router.post("/2fa/verify")
async def verify_two_factor(
    request: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify and enable two-factor authentication"""
    if not current_user.two_factor_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor setup not started"
        )
    
    # Verify the code
    totp = pyotp.TOTP(current_user.two_factor_secret)
    if not totp.verify(request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Enable 2FA
    current_user.two_factor_enabled = True
    db.commit()
    
    # Log the event
    audit_service = AuditService(db)
    await audit_service.log_action(
        "2fa_enabled", "user", str(current_user.id), 
        current_user.id, message="Two-factor authentication enabled"
    )
    
    return {"message": "Two-factor authentication enabled successfully"}

@auth_advanced_router.post("/2fa/disable")
async def disable_two_factor(
    request: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable two-factor authentication"""
    if not current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled"
        )
    
    # Verify the code
    totp = pyotp.TOTP(current_user.two_factor_secret)
    if not totp.verify(request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Disable 2FA
    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    db.commit()
    
    # Log the event
    audit_service = AuditService(db)
    await audit_service.log_action(
        "2fa_disabled", "user", str(current_user.id),
        current_user.id, message="Two-factor authentication disabled"
    )
    
    return {"message": "Two-factor authentication disabled successfully"}

@auth_advanced_router.post("/password/reset-request")
async def request_password_reset(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Request password reset"""
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        # Don't reveal if email exists or not
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Generate reset token
    reset_token = generate_random_string(64)
    
    # Store reset token (in production, store in database with expiration)
    # For now, we'll use a simple in-memory cache
    from app.core.cache import cache
    await cache.set(f"password_reset:{reset_token}", user.id, expire=3600)  # 1 hour
    
    # Send email
    email_service = EmailService()
    background_tasks.add_task(
        email_service.send_password_reset_email,
        user.email,
        user.username,
        reset_token
    )
    
    # Log the event
    audit_service = AuditService(db)
    await audit_service.log_action(
        "password_reset_requested", "user", str(user.id),
        message="Password reset requested"
    )
    
    return {"message": "If the email exists, a reset link has been sent"}

@auth_advanced_router.post("/password/reset-confirm")
async def confirm_password_reset(
    request: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Confirm password reset with token"""
    # Verify token
    from app.core.cache import cache
    user_id = await cache.get(f"password_reset:{request.token}")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Validate new password
    validation_result = validate_password_strength(request.new_password)
    if not validation_result["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password validation failed: {', '.join(validation_result['issues'])}"
        )
    
    # Update password
    user.hashed_password = get_password_hash(request.new_password)
    user.password_changed_at = datetime.utcnow()
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    
    # Remove reset token
    await cache.delete(f"password_reset:{request.token}")
    
    # Log the event
    audit_service = AuditService(db)
    await audit_service.log_action(
        "password_reset_completed", "user", str(user.id),
        user.id, message="Password reset completed successfully"
    )
    
    return {"message": "Password reset successfully"}

@auth_advanced_router.post("/password/change")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change password (authenticated user)"""
    # Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    validation_result = validate_password_strength(request.new_password)
    if not validation_result["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password validation failed: {', '.join(validation_result['issues'])}"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(request.new_password)
    current_user.password_changed_at = datetime.utcnow()
    db.commit()
    
    # Log the event
    audit_service = AuditService(db)
    await audit_service.log_action(
        "password_changed", "user", str(current_user.id),
        current_user.id, message="Password changed successfully"
    )
    
    return {"message": "Password changed successfully"}

@auth_advanced_router.get("/sessions", response_model=list[SessionResponse])
async def get_user_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's active sessions"""
    sessions = db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.status == SessionStatus.ACTIVE
    ).order_by(UserSession.last_activity.desc()).all()
    
    return [
        SessionResponse(
            id=session.id,
            session_id=session.session_id,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            device_info=session.device_info,
            is_current=False,  # TODO: Determine current session
            last_activity=session.last_activity,
            created_at=session.created_at
        )
        for session in sessions
    ]

@auth_advanced_router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke a specific session"""
    session = db.query(UserSession).filter(
        UserSession.session_id == session_id,
        UserSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    session.status = SessionStatus.REVOKED
    session.revoked_at = datetime.utcnow()
    db.commit()
    
    # Log the event
    audit_service = AuditService(db)
    await audit_service.log_action(
        "session_revoked", "session", session_id,
        current_user.id, message="Session revoked by user"
    )
    
    return {"message": "Session revoked successfully"}

@auth_advanced_router.delete("/sessions/all")
async def revoke_all_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke all sessions except current"""
    # TODO: Get current session ID to exclude it
    sessions = db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.status == SessionStatus.ACTIVE
    ).all()
    
    revoked_count = 0
    for session in sessions:
        session.status = SessionStatus.REVOKED
        session.revoked_at = datetime.utcnow()
        revoked_count += 1
    
    db.commit()
    
    # Log the event
    audit_service = AuditService(db)
    await audit_service.log_action(
        "all_sessions_revoked", "user", str(current_user.id),
        current_user.id, message=f"All sessions revoked ({revoked_count} sessions)"
    )
    
    return {"message": f"Revoked {revoked_count} sessions"}

@auth_advanced_router.get("/security", response_model=SecuritySettingsResponse)
async def get_security_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user security settings"""
    return SecuritySettingsResponse(
        two_factor_enabled=current_user.two_factor_enabled,
        password_changed_at=current_user.password_changed_at,
        last_login=current_user.last_login,
        failed_login_attempts=current_user.failed_login_attempts,
        is_locked=current_user.locked_until > datetime.utcnow() if current_user.locked_until else False,
        active_sessions_count=db.query(UserSession).filter(
            UserSession.user_id == current_user.id,
            UserSession.status == SessionStatus.ACTIVE
        ).count()
    )

@auth_advanced_router.put("/security")
async def update_security_settings(
    settings: SecuritySettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user security settings"""
    # Update preferences
    if settings.session_timeout is not None:
        current_user.set_preference("session_timeout", settings.session_timeout)
    
    if settings.login_notifications is not None:
        current_user.set_preference("login_notifications", settings.login_notifications)
    
    if settings.security_emails is not None:
        current_user.set_preference("security_emails", settings.security_emails)
    
    db.commit()
    
    return {"message": "Security settings updated successfully"}

@auth_advanced_router.post("/refresh")
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
    try:
        payload = verify_refresh_token(refresh_token)
        user_id = payload.get("sub")
        
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Generate new access token
        access_token = create_access_token(data={"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@auth_advanced_router.post("/login/advanced")
async def advanced_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    totp_code: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Advanced login with 2FA support"""
    client_ip = get_client_ip(request) if request else "unknown"
    
    # Check if IP/username is locked
    if auth_security.is_locked(client_ip) or auth_security.is_locked(form_data.username):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked due to too many failed attempts"
        )
    
    # Authenticate user
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        # Record failed attempt
        auth_security.record_failed_attempt(client_ip)
        auth_security.record_failed_attempt(form_data.username)
        
        # Log failed attempt
        audit_service = AuditService(db)
        await audit_service.log_action(
            "login_failed", "user", form_data.username,
            ip_address=client_ip, success=False,
            message="Invalid credentials"
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    
    # Check 2FA if enabled
    if user.two_factor_enabled:
        if not totp_code:
            raise HTTPException(
                status_code=status.HTTP_200_OK,  # Special status for 2FA required
                detail="Two-factor authentication required",
                headers={"X-2FA-Required": "true"}
            )
        
        totp = pyotp.TOTP(user.two_factor_secret)
        if not totp.verify(totp_code):
            # Record failed attempt
            auth_security.record_failed_attempt(client_ip)
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid two-factor authentication code"
            )
    
    # Clear failed attempts on successful login
    auth_security.clear_failed_attempts(client_ip)
    auth_security.clear_failed_attempts(form_data.username)
    
    # Update user login info
    user.last_login = datetime.utcnow()
    user.login_count = (user.login_count or 0) + 1
    user.failed_login_attempts = 0
    db.commit()
    
    # Create session
    session = UserSession(
        session_id=generate_random_string(64),
        user_id=user.id,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent") if request else None,
        login_method="password_2fa" if user.two_factor_enabled else "password"
    )
    db.add(session)
    db.commit()
    
    # Generate tokens
    access_token = create_access_token(data={"sub": str(user.id), "session_id": session.session_id})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    # Log successful login
    audit_service = AuditService(db)
    await audit_service.log_action(
        "login_success", "user", str(user.id),
        user.id, ip_address=client_ip,
        message="Successful login"
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "session_id": session.session_id
    }