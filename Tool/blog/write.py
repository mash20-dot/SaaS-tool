from flask import jsonify, request, Blueprint
from app.models import db, Blog, User
from flask_jwt_extended import jwt_required
from blog.decorator import role_required

blog = Blueprint('blog', '__name__')


@blog.route('/bloglist', methods=['POST'])
@jwt_required()
@role_required("admin")
def bloglist():

    data = request.get_json()
    topic = data.get("topic")
    content = data.get("content")

    if not content or not topic:
        return jsonify({
            "message": "please fill in all fields"
        }), 400
    
    new_blog = Blog(
        topic=topic,
        content=content
    )

    db.session.add(new_blog)
    db.session.commit()
    return jsonify({
        "message":"blog uploaded successfully"
    }), 201

@blog.route('/list/bloglist', methods=['GET'])
def list():

    listens = Blog.query.all()

    blogs = []
    for me in listens:
        blogs.append({
            "content":me.content,
            "topic":me.content,
            "created_at":me.created_at
        })

    return jsonify(blogs), 200
