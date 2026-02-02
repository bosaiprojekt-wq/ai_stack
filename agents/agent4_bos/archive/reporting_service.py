# core/university_service.py
from qdrant_client import QdrantClient
from typing import List, Dict, Any, Optional
from .config import QDRANT_HOST, QDRANT_PORT

class UniversityService:
    def __init__(self, collection_name="university_protocols"):
        self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        self.collection_name = collection_name
    
    def get_all_records(self, record_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all records, optionally filtered by type"""
        try:
            scroll_filter = None
            if record_type:
                scroll_filter = {
                    "must": [
                        {"key": "type", "match": {"value": record_type}}
                    ]
                }
            
            points, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=scroll_filter,
                limit=1000,
                with_payload=True
            )
            
            return [dict(point.payload) for point in points]
        except Exception as e:
            print(f"Error getting records: {e}")
            return []
    
    def get_protocols(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get protocols, optionally filtered by status"""
        protocols = self.get_all_records("protocol")
        if status:
            return [p for p in protocols if p.get("status") == status]
        return protocols
    
    def get_professors(self) -> List[Dict[str, Any]]:
        """Get all professors"""
        return self.get_all_records("professor")
    
    def get_groups(self) -> List[Dict[str, Any]]:
        """Get all groups"""
        return self.get_all_records("group")
    
    def get_students(self, group_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get students, optionally filtered by group"""
        students = self.get_all_records("student")
        if group_id:
            return [s for s in students if s.get("group_id") == group_id]
        return students
    
    def get_grades(self, student_id: Optional[str] = None, subject_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get grades with optional filters"""
        grades = self.get_all_records("grade")
        filtered = grades
        
        if student_id:
            filtered = [g for g in filtered if g.get("student_id") == student_id]
        if subject_id:
            filtered = [g for g in filtered if g.get("subject_id") == subject_id]
        
        return filtered
    
    def get_subjects(self, professor_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get subjects, optionally filtered by professor"""
        subjects = self.get_all_records("subject")
        if professor_id:
            return [s for s in subjects if s.get("professor_id") == professor_id]
        return subjects
    
    def get_open_protocols_count(self) -> int:
        """Count open protocols"""
        open_protocols = self.get_protocols(status="open")
        return len(open_protocols)
    
    def get_pending_protocols_count(self) -> int:
        """Count pending protocols"""
        pending_protocols = self.get_protocols(status="pending")
        return len(pending_protocols)
    
    def get_closed_protocols_count(self) -> int:
        """Count closed protocols"""
        closed_protocols = self.get_protocols(status="closed")
        return len(closed_protocols)
    
    def get_professors_with_open_protocols(self) -> List[Dict[str, Any]]:
        """Get professors who have open protocols"""
        open_protocols = self.get_protocols(status="open")
        pending_protocols = self.get_protocols(status="pending")
        
        professor_ids = set()
        for protocol in open_protocols + pending_protocols:
            prof_id = protocol.get("professor_id")
            if prof_id:
                professor_ids.add(prof_id)
        
        all_professors = self.get_professors()
        result = []
        
        for prof in all_professors:
            if prof.get("professor_id") in professor_ids:
                # Get professor's open protocols
                prof_protocols = [p for p in open_protocols + pending_protocols 
                                 if p.get("professor_id") == prof.get("professor_id")]
                # Get professor's subjects
                prof_subjects = self.get_subjects(professor_id=prof.get("professor_id"))
                # Get groups for professor's protocols
                prof_groups = []
                for protocol in prof_protocols:
                    group_id = protocol.get("group_id")
                    if group_id:
                        groups = self.get_all_records("group")
                        group = next((g for g in groups if g.get("group_id") == group_id), None)
                        if group:
                            prof_groups.append(group)
                
                prof_data = prof.copy()
                prof_data["open_protocols"] = prof_protocols
                prof_data["subjects"] = prof_subjects
                prof_data["groups"] = prof_groups
                result.append(prof_data)
        
        return result

# Singleton instance
university_service = UniversityService()