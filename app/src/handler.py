import json
import boto3
import logging
import uuid
import os
from botocore.exceptions import ClientError

# ---------------------------------------------------------
# Setup DynamoDB + Environment
# ---------------------------------------------------------
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))


# ---------------------------------------------------------
# Response helper with CORS for frontend compatibility
# ---------------------------------------------------------
def response(status, body):
    return {
        "statusCode": status,
        "body": json.dumps(body),
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
        },
    }


# ---------------------------------------------------------
# Composite Key Builder (Enterprise Standard)
# PK = tenant#TENANTID#user#USERID
# SK = task#TASKID
# ---------------------------------------------------------
def build_keys(tenant_id, user_id, task_id=None):
    pk = f"tenant#{tenant_id}#user#{user_id}"
    sk = f"task#{task_id}" if task_id else None
    return pk, sk


# ---------------------------------------------------------
# Input Validation
# ---------------------------------------------------------
def validate_path(tenant_id, user_id):
    if not tenant_id or not user_id:
        return False, response(400, {"error": "Missing tenantId or userId"})
    return True, None


def validate_body(event):
    try:
        body = json.loads(event.get("body", "{}"))
        return True, body
    except Exception:
        return False, response(400, {"error": "Invalid JSON in request body"})


# ---------------------------------------------------------
# Main Handler
# ---------------------------------------------------------
def lambda_handler(event, context):
    logger.info("Received event", extra={"event": event})

    http_method = event.get("httpMethod")
    path_params = event.get("pathParameters") or {}

    tenant_id = path_params.get("tenantId")
    user_id = path_params.get("userId")
    task_id = path_params.get("taskId")

    # Validate required path parameters
    ok, err = validate_path(tenant_id, user_id)
    if not ok:
        return err

    # Build keys
    pk, sk = build_keys(tenant_id, user_id, task_id)

    # Route to correct function
    if http_method == "POST":
        return create_task(pk, tenant_id, user_id, event)

    if http_method == "GET":
        return get_task(pk, sk)

    if http_method == "PUT":
        return update_task(pk, sk, event)

    if http_method == "DELETE":
        return delete_task(pk, sk)

    return response(400, {"error": f"Unsupported method {http_method}"})


# ---------------------------------------------------------
# Create Task
# ---------------------------------------------------------
def create_task(pk, tenant_id, user_id, event):
    ok, data = validate_body(event)
    if not ok:
        return data

    if "title" not in data:
        return response(400, {"error": "title is required"})

    task_id = str(uuid.uuid4())
    sk = f"task#{task_id}"

    item = {
        "PK": pk,
        "SK": sk,
        "taskId": task_id,
        "tenantId": tenant_id,
        "userId": user_id,
        "title": data["title"],
        "description": data.get("description"),
        "status": data.get("status", "pending"),
    }

    table.put_item(Item=item)
    return response(201, item)


# ---------------------------------------------------------
# Get Task
# ---------------------------------------------------------
def get_task(pk, sk):
    try:
        result = table.get_item(Key={"PK": pk, "SK": sk})
    except Exception as e:
        logger.error("DynamoDB GetItem failed", extra={"error": str(e)})
        return response(500, {"error": "Internal server error"})

    if "Item" not in result:
        return response(404, {"error": "Task not found"})

    return response(200, result["Item"])


# ---------------------------------------------------------
# Update Task
# ---------------------------------------------------------
def update_task(pk, sk, event):
    ok, data = validate_body(event)
    if not ok:
        return data

    # Prevent updating identity keys
    protected = {"PK", "SK", "tenantId", "userId", "taskId"}

    update_expr = []
    expr_attr = {}

    for k, v in data.items():
        if k not in protected:
            update_expr.append(f"{k} = :{k}")
            expr_attr[f":{k}"] = v

    if not update_expr:
        return response(400, {"error": "No valid fields to update"})

    try:
        result = table.update_item(
            Key={"PK": pk, "SK": sk},
            UpdateExpression="SET " + ", ".join(update_expr),
            ExpressionAttributeValues=expr_attr,
            ConditionExpression="attribute_exists(PK)",
            ReturnValues="ALL_NEW",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return response(404, {"error": "Task not found"})
        raise

    updated_item = result.get("Attributes", {})
    return response(200, {"message": "Task updated", "task": updated_item})


# ---------------------------------------------------------
# Delete Task
# ---------------------------------------------------------
def delete_task(pk, sk):
    try:
        table.delete_item(
            Key={"PK": pk, "SK": sk},
            ConditionExpression="attribute_exists(PK)",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return response(404, {"error": "Task not found"})
        raise

    return response(200, {"message": "Task deleted"})
