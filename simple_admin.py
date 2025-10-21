"""
Admin credentials configuration
These credentials are hardcoded as per requirements
"""

ADMIN_CREDENTIALS = {
    "username": "ayushman.g99@gmail.com",
    "password": "Ganapati@123"
}

def verify_admin(username, password):
    """
    Verify admin credentials
    
    Args:
        username (str): Admin username
        password (str): Admin password
        
    Returns:
        bool: True if credentials are valid, False otherwise
    """
    return (username == ADMIN_CREDENTIALS["username"] and 
            password == ADMIN_CREDENTIALS["password"])

