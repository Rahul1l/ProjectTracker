"""
Project Tracker Flask Application
Single-page application with API routes
"""

from flask import Flask, request, jsonify, session, send_file
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from dotenv import load_dotenv
from bson import ObjectId
import simple_admin

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default-secret-key')

# MongoDB Configuration
MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('DB_NAME', 'project_tracker')

# Initialize MongoDB client
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Collections
trainers_collection = db['trainers']
projects_collection = db['projects']


# Serve the single index.html file
@app.route('/')
def index():
    return send_file('index.html')


# ============= ADMIN API ROUTES =============

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if simple_admin.verify_admin(username, password):
        session['admin_logged_in'] = True
        session['user_type'] = 'admin'
        return jsonify({'success': True, 'message': 'Login successful'})
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401


@app.route('/api/admin/create_trainer', methods=['POST'])
def create_trainer():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.get_json()
    trainer_name = data.get('trainer_name')
    password = data.get('password')
    
    if not trainer_name or not password:
        return jsonify({'success': False, 'message': 'Trainer name and password are required'}), 400
    
    # Check if trainer already exists
    existing_trainer = trainers_collection.find_one({'trainer_name': trainer_name})
    if existing_trainer:
        return jsonify({'success': False, 'message': 'Trainer already exists'}), 400
    
    # Create new trainer
    hashed_password = generate_password_hash(password)
    trainer = {
        'trainer_name': trainer_name,
        'password': hashed_password,
        'created_at': datetime.now()
    }
    
    trainers_collection.insert_one(trainer)
    return jsonify({'success': True, 'message': 'Trainer created successfully'})


@app.route('/api/admin/trainers', methods=['GET'])
def get_trainers():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    trainers = list(trainers_collection.find({}, {'password': 0}))
    for trainer in trainers:
        trainer['_id'] = str(trainer['_id'])
        trainer['created_at'] = trainer['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({'success': True, 'trainers': trainers})


@app.route('/api/admin/trainer/<trainer_id>', methods=['PUT', 'DELETE'])
def manage_trainer(trainer_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if request.method == 'DELETE':
        # Delete trainer and all their projects
        trainers_collection.delete_one({'_id': ObjectId(trainer_id)})
        projects_collection.delete_many({'trainer_id': trainer_id})
        return jsonify({'success': True, 'message': 'Trainer deleted successfully'})
    
    elif request.method == 'PUT':
        data = request.get_json()
        update_data = {}
        
        if 'trainer_name' in data:
            update_data['trainer_name'] = data['trainer_name']
        
        if 'password' in data and data['password']:
            update_data['password'] = generate_password_hash(data['password'])
        
        trainers_collection.update_one(
            {'_id': ObjectId(trainer_id)},
            {'$set': update_data}
        )
        return jsonify({'success': True, 'message': 'Trainer updated successfully'})


@app.route('/api/admin/projects', methods=['GET'])
def get_all_projects():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    # Get all projects with trainer information
    projects = list(projects_collection.find({}))
    
    # Group projects by trainer
    trainer_projects = {}
    for project in projects:
        trainer_id = project['trainer_id']
        trainer = trainers_collection.find_one({'_id': ObjectId(trainer_id)})
        trainer_name = trainer['trainer_name'] if trainer else 'Unknown'
        
        if trainer_name not in trainer_projects:
            trainer_projects[trainer_name] = []
        
        trainer_projects[trainer_name].append({
            '_id': str(project['_id']),
            'date': project['date'],
            'project_name': project['project_name'],
            'project_details': project['project_details'],
            'remarks': project['remarks'],
            'created_at': project['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify({'success': True, 'projects': trainer_projects})


@app.route('/api/admin/project/<project_id>', methods=['PUT', 'DELETE'])
def admin_manage_project(project_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if request.method == 'DELETE':
        result = projects_collection.delete_one({'_id': ObjectId(project_id)})
        
        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': 'Project deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Project not found'}), 404
    
    elif request.method == 'PUT':
        data = request.get_json()
        
        update_data = {
            'date': data.get('date'),
            'project_name': data.get('project_name'),
            'project_details': data.get('project_details'),
            'remarks': data.get('remarks')
        }
        
        result = projects_collection.update_one(
            {'_id': ObjectId(project_id)},
            {'$set': update_data}
        )
        
        if result.modified_count > 0:
            return jsonify({'success': True, 'message': 'Project updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Project not found'}), 404


# ============= USER/TRAINER API ROUTES =============

@app.route('/api/user/login', methods=['POST'])
def user_login():
    data = request.get_json()
    trainer_name = data.get('trainer_name')
    password = data.get('password')
    
    trainer = trainers_collection.find_one({'trainer_name': trainer_name})
    
    if trainer and check_password_hash(trainer['password'], password):
        session['trainer_logged_in'] = True
        session['trainer_id'] = str(trainer['_id'])
        session['trainer_name'] = trainer['trainer_name']
        session['user_type'] = 'trainer'
        return jsonify({'success': True, 'message': 'Login successful', 'trainer_name': trainer['trainer_name']})
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401


@app.route('/api/user/projects', methods=['GET', 'POST'])
def manage_projects():
    if not session.get('trainer_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    trainer_id = session.get('trainer_id')
    
    if request.method == 'POST':
        data = request.get_json()
        
        project = {
            'trainer_id': trainer_id,
            'date': data.get('date'),
            'project_name': data.get('project_name'),
            'project_details': data.get('project_details'),
            'remarks': data.get('remarks'),
            'created_at': datetime.now()
        }
        
        projects_collection.insert_one(project)
        return jsonify({'success': True, 'message': 'Project added successfully'})
    
    # GET - Retrieve trainer's projects
    projects = list(projects_collection.find({'trainer_id': trainer_id}))
    
    # Group projects by project name
    grouped_projects = {}
    for project in projects:
        project_name = project['project_name']
        if project_name not in grouped_projects:
            grouped_projects[project_name] = []
        
        grouped_projects[project_name].append({
            '_id': str(project['_id']),
            'date': project['date'],
            'project_name': project['project_name'],
            'project_details': project['project_details'],
            'remarks': project['remarks'],
            'created_at': project['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify({'success': True, 'projects': grouped_projects})


@app.route('/api/user/project/<project_id>', methods=['PUT', 'DELETE'])
def manage_project(project_id):
    if not session.get('trainer_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    trainer_id = session.get('trainer_id')
    
    if request.method == 'DELETE':
        # Ensure the project belongs to the logged-in trainer
        result = projects_collection.delete_one({
            '_id': ObjectId(project_id),
            'trainer_id': trainer_id
        })
        
        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': 'Project deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Project not found or unauthorized'}), 404
    
    elif request.method == 'PUT':
        data = request.get_json()
        
        update_data = {
            'date': data.get('date'),
            'project_name': data.get('project_name'),
            'project_details': data.get('project_details'),
            'remarks': data.get('remarks')
        }
        
        result = projects_collection.update_one(
            {'_id': ObjectId(project_id), 'trainer_id': trainer_id},
            {'$set': update_data}
        )
        
        if result.modified_count > 0 or result.matched_count > 0:
            return jsonify({'success': True, 'message': 'Project updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Project not found or unauthorized'}), 404


# ============= SESSION CHECK ROUTE =============

@app.route('/api/check_session', methods=['GET'])
def check_session():
    if session.get('admin_logged_in'):
        return jsonify({'logged_in': True, 'user_type': 'admin'})
    elif session.get('trainer_logged_in'):
        return jsonify({
            'logged_in': True, 
            'user_type': 'trainer',
            'trainer_name': session.get('trainer_name')
        })
    return jsonify({'logged_in': False})


# ============= LOGOUT ROUTE =============

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
