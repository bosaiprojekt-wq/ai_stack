# create_university_db.py
import json
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid
from datetime import datetime, timedelta
import random

# Connect to Qdrant
client = QdrantClient(host="localhost", port=6333)

# Collection name
COLLECTION_NAME = "university_protocols"

def create_collection():
    """Create the university protocols collection"""
    try:
        # Delete if exists
        try:
            client.delete_collection(collection_name=COLLECTION_NAME)
            print(f"Deleted existing collection: {COLLECTION_NAME}")
        except:
            pass
        
        # Create new collection
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        print(f"Created collection: {COLLECTION_NAME}")
        return True
    except Exception as e:
        print(f"Error creating collection: {e}")
        return False

def generate_dummy_data():
    """Generate realistic dummy university data"""
    
    # Generate professors
    professors = [
        {
            "professor_id": "PROF001",
            "name": "Dr. Anna Nowak",
            "email": "anna.nowak@uni.edu.pl",
            "faculty": "Informatyka",
            "title": "dr hab.",
            "subjects": ["Algorytmy", "Bazy Danych"],
            "type": "professor"
        },
        {
            "professor_id": "PROF002", 
            "name": "Prof. Jan Kowalski",
            "email": "jan.kowalski@uni.edu.pl",
            "faculty": "Informatyka",
            "title": "prof. dr hab.",
            "subjects": ["Systemy Operacyjne", "Sieci Komputerowe"],
            "type": "professor"
        },
        {
            "professor_id": "PROF003",
            "name": "Dr. Maria Wiśniewska",
            "email": "maria.wisniewska@uni.edu.pl",
            "faculty": "Matematyka",
            "title": "dr",
            "subjects": ["Analiza Matematyczna", "Statystyka"],
            "type": "professor"
        }
    ]
    
    # Generate subjects
    subjects = [
        {
            "subject_id": "SUB001",
            "code": "INF-301",
            "name": "Algorytmy i Struktury Danych",
            "professor_id": "PROF001",
            "faculty": "Informatyka",
            "semester": 3,
            "ects": 6,
            "type": "subject"
        },
        {
            "subject_id": "SUB002",
            "code": "INF-302",
            "name": "Bazy Danych",
            "professor_id": "PROF001",
            "faculty": "Informatyka",
            "semester": 3,
            "ects": 5,
            "type": "subject"
        },
        {
            "subject_id": "SUB003",
            "code": "INF-303",
            "name": "Systemy Operacyjne",
            "professor_id": "PROF002",
            "faculty": "Informatyka",
            "semester": 4,
            "ects": 5,
            "type": "subject"
        },
        {
            "subject_id": "SUB004",
            "code": "MAT-201",
            "name": "Analiza Matematyczna",
            "professor_id": "PROF003",
            "faculty": "Matematyka",
            "semester": 2,
            "ects": 8,
            "type": "subject"
        }
    ]
    
    # Generate groups
    groups = [
        {
            "group_id": "GRP_CS_3A",
            "name": "Grupa 3A Informatyka",
            "faculty": "Informatyka",
            "semester": 3,
            "student_count": 25,
            "protocol_status": "open",
            "type": "group"
        },
        {
            "group_id": "GRP_CS_3B",
            "name": "Grupa 3B Informatyka",
            "faculty": "Informatyka",
            "semester": 3,
            "student_count": 22,
            "protocol_status": "pending",
            "type": "group"
        },
        {
            "group_id": "GRP_CS_4A",
            "name": "Grupa 4A Informatyka",
            "faculty": "Informatyka",
            "semester": 4,
            "student_count": 20,
            "protocol_status": "closed",
            "type": "group"
        },
        {
            "group_id": "GRP_MATH_2A",
            "name": "Grupa 2A Matematyka",
            "faculty": "Matematyka",
            "semester": 2,
            "student_count": 18,
            "protocol_status": "open",
            "type": "group"
        }
    ]
    
    # Generate students
    students = []
    student_names = [
        "Jan Kowalski", "Anna Nowak", "Piotr Wiśniewski", "Maria Dąbrowska",
        "Krzysztof Lewandowski", "Agnieszka Wójcik", "Tomasz Kamiński",
        "Ewa Kowalczyk", "Michał Zieliński", "Magdalena Szymańska",
        "Paweł Woźniak", "Katarzyna Kozłowska", "Adam Jankowski",
        "Joanna Mazur", "Marcin Kwiatkowski"
    ]
    
    for i, name in enumerate(student_names):
        group_idx = i % 4
        student = {
            "student_id": f"ST{i+1:03d}",
            "name": name,
            "email": f"{name.lower().replace(' ', '.')}@student.edu.pl",
            "faculty": groups[group_idx]["faculty"],
            "semester": groups[group_idx]["semester"],
            "group_id": groups[group_idx]["group_id"],
            "type": "student"
        }
        students.append(student)
    
    # Generate protocols
    protocols = [
        {
            "protocol_id": "PROT001",
            "group_id": "GRP_CS_3A",
            "semester": "2024Z",
            "status": "open",
            "deadline": "2024-02-15",
            "professor_id": "PROF001",
            "created_at": "2024-01-10",
            "closed_at": None,
            "type": "protocol"
        },
        {
            "protocol_id": "PROT002",
            "group_id": "GRP_CS_3B",
            "semester": "2024Z",
            "status": "pending",
            "deadline": "2024-02-20",
            "professor_id": "PROF002",
            "created_at": "2024-01-12",
            "closed_at": None,
            "type": "protocol"
        },
        {
            "protocol_id": "PROT003",
            "group_id": "GRP_CS_4A",
            "semester": "2024Z",
            "status": "closed",
            "deadline": "2024-02-10",
            "professor_id": "PROF002",
            "created_at": "2024-01-05",
            "closed_at": "2024-02-11",
            "type": "protocol"
        },
        {
            "protocol_id": "PROT004",
            "group_id": "GRP_MATH_2A",
            "semester": "2024Z",
            "status": "open",
            "deadline": "2024-02-25",
            "professor_id": "PROF003",
            "created_at": "2024-01-15",
            "closed_at": None,
            "type": "protocol"
        }
    ]
    
    # Generate grades
    grades = []
    grade_values = [2.0, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5]
    
    for i, student in enumerate(students[:10]):  # Grades for first 10 students
        for subject in subjects[:2]:  # Grades for first 2 subjects
            grade = {
                "grade_id": f"GRD{i+1:03d}_{subject['subject_id']}",
                "student_id": student["student_id"],
                "subject_id": subject["subject_id"],
                "grade": random.choice(grade_values),
                "date": "2024-01-28",
                "status": "final" if random.random() > 0.3 else "draft",
                "protocol_id": "PROT001" if subject["professor_id"] == "PROF001" else "PROT002",
                "type": "grade"
            }
            grades.append(grade)
    
    # Combine all data
    all_data = professors + subjects + groups + students + protocols + grades
    
    return all_data

def upload_data(data):
    """Upload data to Qdrant"""
    points = []
    
    for item in data:
        point_id = str(uuid.uuid4())
        point = PointStruct(
            id=point_id,
            vector=[0.0] * 384,  # Dummy vector
            payload=item
        )
        points.append(point)
    
    # Upload in batches
    batch_size = 50
    for i in range(0, len(points), batch_size):
        batch = points[i:i+batch_size]
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=batch,
            wait=True
        )
        print(f"Uploaded batch {i//batch_size + 1}/{(len(points)-1)//batch_size + 1}")
    
    return len(points)

def verify_data():
    """Verify the uploaded data"""
    try:
        # Count all records
        count_result = client.count(
            collection_name=COLLECTION_NAME
        )
        total_count = count_result.count
        
        # Get sample records by type
        print(f"\nTotal records in database: {total_count}")
        
        # Get counts by type
        types = ["professor", "subject", "group", "student", "protocol", "grade"]
        for t in types:
            result = client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter={
                    "must": [
                        {"key": "type", "match": {"value": t}}
                    ]
                },
                limit=1000,
                with_payload=True
            )[0]
            print(f"  {t.capitalize()}s: {len(result)}")
        
        # Show some sample data
        print("\nSample data:")
        sample = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=3,
            with_payload=True
        )[0]
        
        for i, point in enumerate(sample):
            print(f"\n{i+1}. {point.payload.get('type', 'unknown')}:")
            print(f"   ID: {point.payload.get('professor_id') or point.payload.get('student_id') or point.payload.get('subject_id') or point.payload.get('group_id') or point.payload.get('protocol_id') or point.payload.get('grade_id')}")
            for key, value in point.payload.items():
                if key not in ['type']:
                    print(f"   {key}: {value}")
        
        return True
    except Exception as e:
        print(f"Error verifying data: {e}")
        return False

def main():
    """Main function to create and populate the database"""
    print("=" * 60)
    print("Creating University Protocols Database")
    print("=" * 60)
    
    # Step 1: Create collection
    print("\n1. Creating collection...")
    if not create_collection():
        return
    
    # Step 2: Generate data
    print("\n2. Generating dummy data...")
    data = generate_dummy_data()
    print(f"   Generated {len(data)} records")
    
    # Step 3: Upload data
    print("\n3. Uploading data to Qdrant...")
    uploaded_count = upload_data(data)
    print(f"   Uploaded {uploaded_count} records")
    
    # Step 4: Verify data
    print("\n4. Verifying data...")
    verify_data()
    
    print("\n" + "=" * 60)
    print("Database creation complete!")
    print(f"Collection: {COLLECTION_NAME}")
    print("=" * 60)

if __name__ == "__main__":
    main()