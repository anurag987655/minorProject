# recognizer.py

import face_recognition
import os

# Load known faces
known_face_encodings = []
known_face_names = []

def load_known_faces(known_faces_dir='known_faces'):
    for filename in os.listdir(known_faces_dir):
        if filename.endswith(('.jpg', '.jpeg', '.png')):
            path = os.path.join(known_faces_dir, filename)
            image = face_recognition.load_image_file(path)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                known_face_encodings.append(encodings[0])
                known_face_names.append(os.path.splitext(filename)[0])

def recognize_face(image_path):
    unknown_image = face_recognition.load_image_file(image_path)
    unknown_encodings = face_recognition.face_encodings(unknown_image)

    if not unknown_encodings:
        return "No face detected"

    for unknown_encoding in unknown_encodings:
        results = face_recognition.compare_faces(known_face_encodings, unknown_encoding)
        if True in results:
            first_match_index = results.index(True)
            return known_face_names[first_match_index]
    return "Unknown"

# Load known faces at the start
load_known_faces()
