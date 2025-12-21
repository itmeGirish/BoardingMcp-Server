import base64

def generate_token(username, password, project_id):
    # Combine with colon format
    raw_string = f"{username}:{password}:{project_id}"
    
    # Encode to Base64 (UTF-8)
    token = base64.b64encode(raw_string.encode("utf-8")).decode("utf-8")
    
    return token

# # Example usage:
# username = "girish"
# password = "MyPass123"
# project_id = "project001"

# token = generate_token(username, password, project_id)
# print("Encoded Token:", token)
