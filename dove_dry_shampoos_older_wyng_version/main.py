import json

def lambda_handler(event, context):
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "hello from dove dry shampoos",
            # "location": ip.text.replace("\n", "")
        }),
    }
