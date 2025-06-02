# app/services/search_service.py
"""
Advanced Search Service
"""

import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, text
from datetime import datetime

from app.models.user import User, File
from app.schemas.search import SearchRequest, SearchFilter
from app.services.cache_service import CacheService


class SearchService:
    def __init__(self, db: Session):
        self.db = db
        self.cache = CacheService()

    async def search(
            self,
            query: str,
            search_type: str,
            user_id: int,
            limit: int = 20,
            offset: int = 0
    ) -> Dict[str, Any]:
        """Universal search functionality"""

        # Normalize query
        query = query.strip().lower()
        if not query:
            return {"results": [], "total": 0}

        # Cache key
        cache_key = f"search:{user_id}:{search_type}:{query}:{limit}:{offset}"

        # Check cache
        cached_result = await self.cache.get_user_cache(user_id, cache_key)
        if cached_result:
            return cached_result

        results = []
        total = 0

        if search_type in ["all", "files"]:
            file_results = await self._search_files(query, user_id, limit, offset)
            results.extend(file_results["results"])
            total += file_results["total"]

        if search_type in ["all", "users"] and total < limit:
            # Only search users if we haven't reached limit with files
            remaining_limit = limit - len(results)
            user_results = await self._search_users(query, user_id, remaining_limit, 0)
            results.extend(user_results["results"])
            total += user_results["total"]

        # Sort by relevance
        results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        result = {
            "results": results[:limit],
            "total": total,
            "query": query,
            "search_type": search_type
        }

        # Cache for 5 minutes
        await self.cache.set_user_cache(user_id, cache_key, result, 300)

        return result

    async def _search_files(self, query: str, user_id: int, limit: int, offset: int) -> Dict[str, Any]:
        """Search files with relevance scoring"""

        search_terms = query.split()

        # Build query
        base_query = self.db.query(File).filter(
            and_(
                File.owner_id == user_id,
                File.is_deleted == False
            )
        )

        # Add search conditions
        search_conditions = []
        for term in search_terms:
            term_condition = or_(
                func.lower(File.name).contains(term),
                func.lower(File.description).contains(term),
                func.lower(File.tags).contains(term)
            )
            search_conditions.append(term_condition)

        if search_conditions:
            base_query = base_query.filter(and_(*search_conditions))

        # Get total count
        total = base_query.count()

        # Get results
        files = base_query.order_by(File.updated_at.desc()).offset(offset).limit(limit).all()

        results = []
        for file in files:
            relevance_score = self._calculate_file_relevance(file, search_terms)
            results.append({
                "id": file.id,
                "name": file.name,
                "type": "file",
                "file_type": file.file_type,
                "path": file.path,
                "size": file.size,
                "created_at": file.created_at,
                "updated_at": file.updated_at,
                "relevance_score": relevance_score
            })

        return {"results": results, "total": total}

    async def _search_users(self, query: str, current_user_id: int, limit: int, offset: int) -> Dict[str, Any]:
        """Search users (for admin or shared content)"""

        # Basic user search (could be expanded based on permissions)
        users = self.db.query(User).filter(
            and_(
                User.id != current_user_id,
                or_(
                    func.lower(User.username).contains(query),
                    func.lower(User.first_name).contains(query),
                    func.lower(User.last_name).contains(query)
                )
            )
        ).offset(offset).limit(limit).all()

        results = []
        for user in users:
            results.append({
                "id": user.id,
                "name": user.username,
                "type": "user",
                "full_name": user.full_name,
                "created_at": user.created_at,
                "relevance_score": self._calculate_user_relevance(user, query)
            })

        return {"results": results, "total": len(results)}

    def _calculate_file_relevance(self, file: File, search_terms: List[str]) -> float:
        """Calculate file search relevance score"""
        score = 0.0

        for term in search_terms:
            # File name match (highest weight)
            if term in file.name.lower():
                score += 10.0
                # Exact match bonus
                if file.name.lower() == term:
                    score += 20.0

            # Description match
            if file.description and term in file.description.lower():
                score += 5.0

            # Tag match
            if file.tags and term in str(file.tags).lower():
                score += 7.0

            # File type match
            if file.file_type and term in file.file_type.lower():
                score += 3.0

        # Recent files get bonus
        days_old = (datetime.utcnow() - file.created_at).days
        if days_old < 7:
            score += 2.0
        elif days_old < 30:
            score += 1.0

        return score

    def _calculate_user_relevance(self, user: User, query: str) -> float:
        """Calculate user search relevance score"""
        score = 0.0

        query_lower = query.lower()

        # Username match
        if query_lower in user.username.lower():
            score += 10.0
            if user.username.lower() == query_lower:
                score += 15.0

        # Name matches
        if user.first_name and query_lower in user.first_name.lower():
            score += 8.0

        if user.last_name and query_lower in user.last_name.lower():
            score += 8.0

        return score

    async def advanced_search(self, search_request: SearchRequest, user_id: int) -> Dict[str, Any]:
        """Advanced search with filters"""

        base_query = self.db.query(File).filter(
            and_(
                File.owner_id == user_id,
                File.is_deleted == False
            )
        )

        # Apply text search
        if search_request.query:
            search_terms = search_request.query.lower().split()
            search_conditions = []

            for term in search_terms:
                term_condition = or_(
                    func.lower(File.name).contains(term),
                    func.lower(File.description).contains(term)
                )
                search_conditions.append(term_condition)

            base_query = base_query.filter(and_(*search_conditions))

        # Apply filters
        if search_request.filters:
            filters = search_request.filters

            if filters.file_type:
                base_query = base_query.filter(File.file_type == filters.file_type)

            if filters.size_min:
                base_query = base_query.filter(File.size >= filters.size_min)

            if filters.size_max:
                base_query = base_query.filter(File.size <= filters.size_max)

            if filters.date_from:
                base_query = base_query.filter(File.created_at >= filters.date_from)

            if filters.date_to:
                base_query = base_query.filter(File.created_at <= filters.date_to)

            if filters.tags:
                # Simple tag search (could be improved with proper tag indexing)
                for tag in filters.tags:
                    base_query = base_query.filter(
                        func.lower(File.tags).contains(tag.lower())
                    )

        # Get total count
        total = base_query.count()

        # Get results with pagination
        files = base_query.order_by(
            File.updated_at.desc()
        ).offset(search_request.offset).limit(search_request.limit).all()

        results = []
        for file in files:
            results.append({
                "id": file.id,
                "name": file.name,
                "type": "file",
                "file_type": file.file_type,
                "path": file.path,
                "size": file.size,
                "created_at": file.created_at,
                "updated_at": file.updated_at,
                "tags": file.get_tag_list() if hasattr(file, 'get_tag_list') else []
            })

        return {
            "results": results,
            "total": total,
            "query": search_request.query,
            "filters_applied": search_request.filters is not None
        }

    async def get_suggestions(self, query: str, user_id: int) -> List[str]:
        """Get search suggestions based on query"""

        if len(query) < 2:
            return []

        # Get recent file names that match
        file_names = self.db.query(File.name).filter(
            and_(
                File.owner_id == user_id,
                File.is_deleted == False,
                func.lower(File.name).contains(query.lower())
            )
        ).limit(10).all()

        suggestions = list(set([name.name for name in file_names]))

        # Add common file type suggestions
        if any(keyword in query.lower() for keyword in ['image', 'photo', 'picture']):
            suggestions.extend(['images', 'photos', 'pictures'])

        if any(keyword in query.lower() for keyword in ['document', 'doc', 'text']):
            suggestions.extend(['documents', 'text files'])

        if any(keyword in query.lower() for keyword in ['video', 'movie']):
            suggestions.extend(['videos', 'movies'])

        return suggestions[:10]