from flask import jsonify, request, Blueprint
from app.models import db, Blog, User
from flask_jwt_extended import jwt_required, get_jwt_identity
from blog.decorator import role_required

blog = Blueprint('blog', __name__)  # Fixed: __name__ without quotes


# Helper function to check if user is admin
def is_admin():
    email = get_jwt_identity()
    user = User.query.filter_by(email=email).first()
    return user and user.role

# ------------------------------
# CREATE BLOG POST (ADMIN ONLY)
# ------------------------------
@blog.route('/posts', methods=['POST', 'OPTIONS'])
@jwt_required()
@role_required("admin")
def create_blog():
    
     # Get author from current user
    current_email = get_jwt_identity()
    user = User.query.filter_by(email=current_email).first()
    
    if not user:
        return jsonify({
            "message": "user not found"
        }), 400


    data = request.get_json()
    topic = data.get("topic", "").strip()
    content = data.get("content", "").strip()
    excerpt = data.get("excerpt", "").strip()
    image = data.get("image", "")
    published = data.get("published", False)
    author = user.business_name or user.email

   
    # Validation
    #if not topic or len(topic) < 5:
        #return jsonify({"error": "Topic must be at least 5 characters"}), 400
    
    if not content or len(content) < 50:
        return jsonify({"error": "Content must be at least 50 characters"}), 400
    
    if not excerpt or len(excerpt) < 20:
        return jsonify({"error": "Excerpt must be at least 20 characters"}), 400
    
    new_blog = Blog(
        topic=topic,
        content=content,
        excerpt=excerpt,
        image=image,
        author=author,
        published=published
    )

    db.session.add(new_blog)
    db.session.commit()
    
    return jsonify({
        "message": "Blog post created successfully",
        "post_id": new_blog.id
    }), 201




# ------------------------------
# GET ALL POSTS (ADMIN - includes drafts)
# ------------------------------
@blog.route('/posts/all', methods=['GET', 'OPTIONS'])
@jwt_required()
@role_required("admin")
def get_all_posts():
    #if request.method == "OPTIONS":
        #return jsonify({"message": "Preflight OK"}), 200
    
    current_email = get_jwt_identity()
    current_user = User.query.filter_by(email=current_email).first()
    if not current_user:
        return jsonify({
            "message": "user not found"
        }), 400
    
    posts = Blog.query.order_by(Blog.created_at.desc()).all()
    
    blogs = []
    for post in posts:
        blogs.append({
            "id": post.id,
            "title": post.topic, 
            "content": post.content,
            "excerpt": post.excerpt,
            "author": post.author,
            "image": post.image,
            "created_at": post.created_at.isoformat(),
            "published": post.published
        })
    
    return jsonify({"posts": blogs}), 200


# ------------------------------
# GET PUBLISHED POSTS (PUBLIC)
# ------------------------------
@blog.route('/posts', methods=['GET', 'OPTIONS'])
def get_published_posts():
    if request.method == "OPTIONS":
        return jsonify({"message": "Preflight OK"}), 200

    
    posts = Blog.query.filter_by(published=True).order_by(Blog.created_at.desc()).all()
    
    blogs = []
    for post in posts:
        blogs.append({
            "id": post.id,
            "title": post.topic,
            "excerpt": post.excerpt,
            "author": post.author,
            "image": post.image,
            "created_at": post.created_at.isoformat()
        })
    
    return jsonify({"posts": blogs}), 200


# ------------------------------
# GET SINGLE POST
# ------------------------------
@blog.route('/posts/<int:post_id>', methods=['GET', 'OPTIONS'])
def get_single_post(post_id):
    if request.method == "OPTIONS":
        return jsonify({"message": "Preflight OK"}), 200
    
    post = Blog.query.get_or_404(post_id)
    
    # If post is not published, require admin access
    if not post.published:
        try:
            jwt_required()(lambda: None)()
            if not is_admin():
                return jsonify({"error": "Post not found"}), 404
        except:
            return jsonify({"error": "Post not found"}), 404
    
    return jsonify({
        "id": post.id,
        "title": post.topic,
        "content": post.content,
        "excerpt": post.excerpt,
        "author": post.author,
        "image": post.image,
        "created_at": post.created_at.isoformat(),
        "published": post.published
    }), 200


# ------------------------------
# UPDATE POST (ADMIN ONLY)
# ------------------------------
@blog.route('/posts/<int:post_id>', methods=['PUT', 'OPTIONS'])
@jwt_required()
@role_required("admin")
def update_post(post_id):
    #if request.method == "OPTIONS":
        #return jsonify({"message": "Preflight OK"}), 200
    
    current_email = get_jwt_identity()
    current_user = User.query.filter_by(email=current_email).first()

    if not current_user:
        return jsonify({
            "message": "user not found"
        }), 400
    
    post = Blog.query.get_or_404(post_id)
    data = request.get_json()
    
    topic = data.get("title", post.topic).strip()  
    content = data.get("content", post.content).strip()
    excerpt = data.get("excerpt", post.excerpt).strip()
    image = data.get("image", post.image)
    published = data.get("published", post.published)
    
    # Validation
    if len(topic) < 5:
        return jsonify({"error": "Topic must be at least 5 characters"}), 400
    
    if len(content) < 50:
        return jsonify({"error": "Content must be at least 50 characters"}), 400
    
    if len(excerpt) < 20:
        return jsonify({"error": "Excerpt must be at least 20 characters"}), 400
    
    post.topic = topic
    post.content = content
    post.excerpt = excerpt
    post.image = image
    post.published = published
    
    db.session.commit()
    
    return jsonify({"message": "Post updated successfully"}), 200


# ------------------------------
# TOGGLE PUBLISH STATUS (ADMIN ONLY)
# ------------------------------
@blog.route('/posts/<int:post_id>/publish', methods=['PUT', 'OPTIONS'])
@jwt_required()
@role_required("admin")
def toggle_publish(post_id):
    if request.method == "OPTIONS":
        return jsonify({"message": "Preflight OK"}), 200
    
    current_email = get_jwt_identity()
    current_user = User.query.filter_by(email=current_email).first()
    if not current_user:
        return jsonify({
            "message": "user not found "
        }), 400
    
    post = Blog.query.get_or_404(post_id)
    data = request.get_json()
    
    post.published = data.get("published", not post.published)
    
    db.session.commit()
    
    return jsonify({
        "message": "Post status updated",
        "published": post.published
    }), 200


# ------------------------------
# DELETE POST (ADMIN ONLY)
# ------------------------------
@blog.route('/posts/<int:post_id>', methods=['DELETE', 'OPTIONS'])
@jwt_required()
@role_required("admin")
def delete_post(post_id):
    #if request.method == "OPTIONS":
        #return jsonify({"message": "Preflight OK"}), 200
    
    current_email = get_jwt_identity()

    current_user = User.query.filter_by(email=current_email).first()
    if not current_user:
        return jsonify({
            "message": "user not found "
        }), 400



    post = Blog.query.get_or_404(post_id)
    
    db.session.delete(post)
    db.session.commit()
    
    return jsonify({"message": "Post deleted successfully"}), 200


# ------------------------------
# LEGACY ROUTES (for backward compatibility)
# ------------------------------
#@blog.route('/bloglist', methods=['POST', 'OPTIONS'])
#@jwt_required()
#@role_required("admin")
#def bloglist_legacy():
    #"""Legacy endpoint - redirects to new create_blog"""
    #return create_blog()


#@blog.route('/list/bloglist', methods=['GET', 'OPTIONS'])
#def list_legacy():
    #"""Legacy endpoint - redirects to new get_published_posts"""
    #return get_published_posts()