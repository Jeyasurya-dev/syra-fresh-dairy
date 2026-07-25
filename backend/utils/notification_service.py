"""
SYRA Fresh - Notification Service
Centralized service for email, SMS, WhatsApp, and in-app notifications.
"""
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from extensions import notifications_col, notification_logs_col, users_col, delivery_boys_col, admins_col


def _as_object_id(value):
    """Normalize an id that may arrive as a str or an ObjectId to ObjectId.

    BUG FIX: orders_col stores `user_id` as a plain string (see order_routes.py),
    so callers like delivery_routes.py invoked notify_customer(order["user_id"], ...)
    with a string. That string was saved as `recipient_id` verbatim. But
    notifications_routes.py looks up a customer's notifications using
    request.current_user["_id"], which is a real ObjectId. MongoDB treats an
    ObjectId and the equal-looking string as different values, so every
    customer notification was created but could never be found again -
    GET /api/notifications always came back empty for customers. Normalizing
    to ObjectId here (matching how delivery boy / admin ids are already
    stored) fixes that without touching the orders schema.
    """
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError):
        return value


class NotificationService:
    """Centralized notification handler."""
    
    NOTIFICATION_TYPES = {
        "order_placed": "Order Placed",
        "order_packed": "Order Packed",
        "order_shipped": "Order Shipped",
        "order_out_for_delivery": "Out For Delivery",
        "order_delivered": "Order Delivered",
        "order_cancelled": "Order Cancelled",
        "order_refund": "Refund Processed",
        "delivery_boy_assigned": "Delivery Boy Assigned",
        "delivery_new_assignment": "New Delivery Assignment",
        "delivery_cancelled": "Delivery Cancelled",
        "delivery_reminder": "Delivery Reminder",
        "admin_new_registration": "New Delivery Boy Registration",
        "admin_new_order": "New Order",
        "admin_failed_delivery": "Failed Delivery",
    }
    
    @staticmethod
    def notify_customer(customer_id, notification_type, data, channels=None):
        """
        Send notification to customer.
        
        data: {order_id, order_number, message, extra_info, ...}
        channels: ["email", "sms", "whatsapp", "in_app"] (default: all)
        """
        if channels is None:
            channels = ["in_app"]
        
        notification_doc = {
            "recipient_id": _as_object_id(customer_id),
            "recipient_type": "customer",
            "notification_type": notification_type,
            "title": NotificationService.NOTIFICATION_TYPES.get(notification_type, notification_type),
            "data": data,
            "channels": channels,
            "read": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        
        result = notifications_col.insert_one(notification_doc)
        
        # Log the notification
        for channel in channels:
            NotificationService._log_notification(result.inserted_id, channel, "queued")
        
        return result.inserted_id
    
    @staticmethod
    def notify_delivery_boy(delivery_boy_id, notification_type, data, channels=None):
        """Send notification to delivery boy."""
        if channels is None:
            channels = ["in_app"]
        
        notification_doc = {
            "recipient_id": delivery_boy_id,
            "recipient_type": "delivery_boy",
            "notification_type": notification_type,
            "title": NotificationService.NOTIFICATION_TYPES.get(notification_type, notification_type),
            "data": data,
            "channels": channels,
            "read": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        
        result = notifications_col.insert_one(notification_doc)
        
        for channel in channels:
            NotificationService._log_notification(result.inserted_id, channel, "queued")
        
        return result.inserted_id
    
    @staticmethod
    def notify_admin(admin_id, notification_type, data, channels=None):
        """Send notification to admin."""
        if channels is None:
            channels = ["in_app"]
        
        notification_doc = {
            "recipient_id": admin_id,
            "recipient_type": "admin",
            "notification_type": notification_type,
            "title": NotificationService.NOTIFICATION_TYPES.get(notification_type, notification_type),
            "data": data,
            "channels": channels,
            "read": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        
        result = notifications_col.insert_one(notification_doc)
        
        for channel in channels:
            NotificationService._log_notification(result.inserted_id, channel, "queued")
        
        return result.inserted_id
    
    @staticmethod
    def notify_broadcast(notification_type, data, recipient_type="all", channels=None):
        """Send broadcast notification to all users of a type."""
        if channels is None:
            channels = ["in_app"]
        
        title = NotificationService.NOTIFICATION_TYPES.get(notification_type, notification_type)
        
        # Find all recipients based on type
        if recipient_type == "customer":
            recipients = users_col.find({"role": "customer"}, {"_id": 1})
        elif recipient_type == "delivery_boy":
            recipients = delivery_boys_col.find({"status": "approved"}, {"_id": 1})
        elif recipient_type == "admin":
            recipients = admins_col.find({}, {"_id": 1})
        else:
            return []
        
        notification_ids = []
        for recipient in recipients:
            notification_doc = {
                "recipient_id": recipient["_id"],
                "recipient_type": recipient_type,
                "notification_type": notification_type,
                "title": title,
                "data": data,
                "channels": channels,
                "read": False,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            
            result = notifications_col.insert_one(notification_doc)
            notification_ids.append(result.inserted_id)
            
            for channel in channels:
                NotificationService._log_notification(result.inserted_id, channel, "queued")
        
        return notification_ids
    
    @staticmethod
    def send_email(recipient_email, subject, message_body, template_data=None):
        """
        Send email notification.
        
        In production, integrate with SendGrid, AWS SES, or similar.
        For now, this is a placeholder that logs the intent.
        """
        log_doc = {
            "delivery_type": "email",
            "recipient": recipient_email,
            "subject": subject,
            "message_body": message_body,
            "template_data": template_data,
            "status": "pending",
            "sent_at": None,
            "error": None,
            "created_at": datetime.now(timezone.utc),
        }
        
        result = notification_logs_col.insert_one(log_doc)
        # TODO: Integrate with email service provider
        return result.inserted_id
    
    @staticmethod
    def send_sms(phone_number, message, provider="twilio"):
        """
        Send SMS notification.
        
        Supports multiple providers: twilio, fast2sms, textlocal
        """
        log_doc = {
            "delivery_type": "sms",
            "provider": provider,
            "recipient": phone_number,
            "message": message,
            "status": "pending",
            "sent_at": None,
            "error": None,
            "created_at": datetime.now(timezone.utc),
        }
        
        result = notification_logs_col.insert_one(log_doc)
        # TODO: Integrate with SMS service provider
        return result.inserted_id
    
    @staticmethod
    def send_whatsapp(phone_number, template_name, template_data, provider="meta"):
        """
        Send WhatsApp notification using template.
        
        Supports Meta WhatsApp Cloud API.
        """
        log_doc = {
            "delivery_type": "whatsapp",
            "provider": provider,
            "recipient": phone_number,
            "template_name": template_name,
            "template_data": template_data,
            "status": "pending",
            "sent_at": None,
            "error": None,
            "created_at": datetime.now(timezone.utc),
        }
        
        result = notification_logs_col.insert_one(log_doc)
        # TODO: Integrate with Meta WhatsApp Cloud API
        return result.inserted_id
    
    @staticmethod
    def _log_notification(notification_id, channel, status):
        """Log notification delivery attempt."""
        log_doc = {
            "notification_id": notification_id,
            "channel": channel,
            "status": status,  # queued, sent, failed, bounced
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        notification_logs_col.insert_one(log_doc)


class EmailTemplates:
    """Email template definitions."""
    
    @staticmethod
    def order_placed(customer_name, order_number, order_total):
        return {
            "subject": f"Order Confirmed: {order_number}",
            "body": f"""
            Hi {customer_name},
            
            Your order {order_number} has been placed successfully.
            Order Total: ₹{order_total}
            
            We will notify you once your order is packed and shipped.
            
            Thank you for shopping with SYRA Fresh!
            """
        }
    
    @staticmethod
    def order_shipped(customer_name, order_number, delivery_boy_name, delivery_boy_phone):
        return {
            "subject": f"Order Shipped: {order_number}",
            "body": f"""
            Hi {customer_name},
            
            Your order {order_number} is on its way!
            Delivery Boy: {delivery_boy_name}
            Contact: {delivery_boy_phone}
            
            Track your order in real-time.
            """
        }
    
    @staticmethod
    def order_delivered(customer_name, order_number):
        return {
            "subject": f"Order Delivered: {order_number}",
            "body": f"""
            Hi {customer_name},
            
            Your order {order_number} has been delivered successfully.
            Thank you for your purchase!
            
            Please rate your delivery experience.
            """
        }
    
    @staticmethod
    def delivery_assignment(delivery_boy_name, order_number, customer_address):
        return {
            "subject": f"New Delivery Assignment: {order_number}",
            "body": f"""
            Hi {delivery_boy_name},
            
            You have been assigned a new delivery:
            Order: {order_number}
            Delivery Address: {customer_address}
            
            Please pick up the order and complete delivery at the earliest.
            """
        }
    
    @staticmethod
    def password_reset(name, reset_link):
        return {
            "subject": "Reset Your Password",
            "body": f"""
            Hi {name},
            
            Click the link below to reset your password:
            {reset_link}
            
            This link will expire in 24 hours.
            
            If you didn't request this, please ignore this email.
            """
        }


class SMSTemplates:
    """SMS template definitions."""
    
    @staticmethod
    def order_placed(order_number):
        return f"Order {order_number} placed successfully. Track: syra.app/track/{order_number}"
    
    @staticmethod
    def order_shipped(order_number, delivery_boy_phone):
        return f"Order {order_number} shipped! Driver: {delivery_boy_phone}. Track real-time."
    
    @staticmethod
    def order_delivered(order_number):
        return f"Order {order_number} delivered. Thank you!"
    
    @staticmethod
    def delivery_assignment(order_number):
        return f"New order: {order_number}. Customer waiting. Pickup now!"


class WhatsAppTemplates:
    """WhatsApp template definitions using Meta Cloud API."""
    
    TEMPLATES = {
        "order_confirmation": {
            "template_name": "order_confirmation",
            "language": "en",
            "parameters": ["order_number", "order_total", "estimated_delivery"]
        },
        "order_shipped": {
            "template_name": "order_shipped",
            "language": "en",
            "parameters": ["order_number", "delivery_boy_name", "delivery_boy_phone"]
        },
        "order_delivered": {
            "template_name": "order_delivered",
            "language": "en",
            "parameters": ["order_number", "order_total"]
        },
        "delivery_assignment": {
            "template_name": "delivery_assignment",
            "language": "en",
            "parameters": ["order_number", "customer_name", "customer_phone"]
        },
        "otp_verification": {
            "template_name": "otp_verification",
            "language": "en",
            "parameters": ["otp"]
        }
    }
