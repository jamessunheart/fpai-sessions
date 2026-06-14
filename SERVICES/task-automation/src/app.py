#!/usr/bin/env python3
"""
Task Automation Framework - Web Dashboard
Flask-based web interface for task monitoring and management
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import Task, TaskType, TaskStatus, AutomationLevel
from src.database import TaskDatabase
from src.task_analyzer import TaskAnalyzer

app = Flask(__name__)
db = TaskDatabase()


@app.route('/')
def index():
    """Main dashboard"""
    stats = db.get_stats()
    recent_tasks = db.list_tasks(limit=20)

    return render_template('index.html',
                         stats=stats,
                         tasks=recent_tasks)


@app.route('/tasks')
def tasks_list():
    """Task list page with filters"""
    status_filter = request.args.get('status')
    service_filter = request.args.get('service')

    status = TaskStatus(status_filter) if status_filter else None
    tasks = db.list_tasks(status=status, service=service_filter, limit=100)

    return render_template('tasks.html', tasks=tasks)


@app.route('/task/<task_id>')
def task_detail(task_id):
    """Task detail page"""
    task = db.get_task(task_id)

    if not task:
        return "Task not found", 404

    return render_template('task_detail.html', task=task)


@app.route('/create', methods=['GET', 'POST'])
def create_task():
    """Create new task"""
    if request.method == 'GET':
        return render_template('create_task.html',
                             task_types=[t.value for t in TaskType])

    # Handle form submission
    task = Task(
        type=TaskType(request.form['type']),
        service=request.form['service'],
        description=request.form['description'],
        params=json.loads(request.form.get('params', '{}'))
    )

    # Auto-analyze if API key available
    if os.environ.get('ANTHROPIC_API_KEY') and request.form.get('analyze'):
        try:
            analyzer = TaskAnalyzer()
            analysis = analyzer.analyze_task(task)
            task.automation_level = analysis.automation_level
            if analysis.blockers_identified:
                task.blocker = analysis.blockers_identified[0]
        except Exception as e:
            print(f"Analysis failed: {e}")

    db.create_task(task)

    return redirect(url_for('task_detail', task_id=task.id))


@app.route('/api/tasks', methods=['GET'])
def api_tasks():
    """API endpoint for tasks"""
    status = request.args.get('status')
    service = request.args.get('service')

    status_filter = TaskStatus(status) if status else None
    tasks = db.list_tasks(status=status_filter, service=service)

    return jsonify([
        {
            'id': t.id,
            'type': t.type,
            'service': t.service,
            'description': t.description,
            'status': t.status,
            'automation_level': t.automation_level,
            'created_at': t.created_at.isoformat(),
            'blocker': t.blocker
        }
        for t in tasks
    ])


@app.route('/api/stats', methods=['GET'])
def api_stats():
    """API endpoint for statistics"""
    return jsonify(db.get_stats())


@app.route('/api/task/<task_id>', methods=['GET'])
def api_task(task_id):
    """API endpoint for single task"""
    task = db.get_task(task_id)

    if not task:
        return jsonify({'error': 'Task not found'}), 404

    return jsonify({
        'id': task.id,
        'type': task.type,
        'service': task.service,
        'description': task.description,
        'status': task.status,
        'automation_level': task.automation_level,
        'blocker': task.blocker,
        'blocker_details': task.blocker_details,
        'created_at': task.created_at.isoformat(),
        'started_at': task.started_at.isoformat() if task.started_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
        'params': task.params,
        'result': task.result,
        'logs': task.logs,
        'error_message': task.error_message
    })


@app.route('/health')
def health():
    """Health check"""
    return jsonify({'status': 'healthy', 'service': 'task-automation'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8031, debug=False)
