# Manufacturing API Documentation

This document provides comprehensive information about the Manufacturing Orders (MO) and Purchase Orders (PO) API endpoints for frontend integration.

## Base URL
```
http://localhost:8000/api/manufacturing/
```

## Authentication
All endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

---

## Manufacturing Orders API

### 1. List Manufacturing Orders
**GET** `/api/manufacturing-orders/`

**Query Parameters:**
- `status`: Filter by status (draft, submitted, gm_approved, rm_allocated, in_progress, completed, cancelled, on_hold)
- `priority`: Filter by priority (low, medium, high, urgent)
- `shift`: Filter by shift (I, II, III)
- `material_type`: Filter by material type (coil, sheet)
- `assigned_supervisor`: Filter by supervisor ID
- `start_date`: Filter from date (YYYY-MM-DD)
- `end_date`: Filter to date (YYYY-MM-DD)
- `search`: Search in mo_id, product_code, part_number, customer_order_reference
- `ordering`: Order by field (created_at, planned_start_date, delivery_date, mo_id). Use `-` for descending
- `page`: Page number for pagination
- `page_size`: Number of items per page (default: 20)

**Example Request:**
```
GET /api/manufacturing-orders/?status=in_progress&priority=high&ordering=-created_at&page=1
```

**Response:**
```json
{
  "count": 25,
  "next": "http://localhost:8000/api/manufacturing-orders/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "mo_id": "MO-20240115-0001",
      "date_time": "2024-01-15T10:30:00Z",
      "product_code": {
        "id": 1,
        "product_code": "SPRING-001",
        "part_number": "SP001",
        "part_name": "Compression Spring"
      },
      "quantity": 100,
      "status": "in_progress",
      "status_display": "In Progress",
      "priority": "high",
      "priority_display": "High",
      "shift": "I",
      "shift_display": "9AM-5PM",
      "assigned_supervisor": {
        "id": 2,
        "email": "supervisor@example.com",
        "first_name": "John",
        "last_name": "Doe"
      },
      "planned_start_date": "2024-01-15T09:00:00Z",
      "planned_end_date": "2024-01-20T17:00:00Z",
      "delivery_date": "2024-01-25",
      "created_by": {
        "id": 1,
        "email": "admin@example.com",
        "first_name": "Admin",
        "last_name": "User"
      },
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### 2. Create Manufacturing Order
**POST** `/api/manufacturing-orders/`

**Request Body:**
```json
{
  "product_code_id": 1,
  "quantity": 100,
  "assigned_supervisor_id": 2,
  "shift": "I",
  "planned_start_date": "2024-01-15T09:00:00Z",
  "planned_end_date": "2024-01-20T17:00:00Z",
  "priority": "high",
  "delivery_date": "2024-01-25",
  "customer_order_reference": "CUST-001",
  "special_instructions": "Handle with care"
}
```

**Response:** Returns the created MO with auto-populated fields

### 3. Get Manufacturing Order Details
**GET** `/api/manufacturing-orders/{id}/`

**Response:**
```json
{
  "id": 1,
  "mo_id": "MO-20240115-0001",
  "date_time": "2024-01-15T10:30:00Z",
  "product_code": {
    "id": 1,
    "product_code": "SPRING-001",
    "part_number": "SP001",
    "part_name": "Compression Spring"
  },
  "quantity": 100,
  "product_type": "Spring",
  "material_name": "Spring Steel",
  "material_type": "coil",
  "grade": "EN42J",
  "wire_diameter_mm": "2.500",
  "thickness_mm": null,
  "finishing": "Zinc Plated",
  "manufacturer_brand": "Tata Steel",
  "weight_kg": "5.000",
  "loose_fg_stock": 0,
  "rm_required_kg": "25.000",
  "assigned_supervisor": {
    "id": 2,
    "email": "supervisor@example.com",
    "first_name": "John",
    "last_name": "Doe"
  },
  "shift": "I",
  "shift_display": "9AM-5PM",
  "planned_start_date": "2024-01-15T09:00:00Z",
  "planned_end_date": "2024-01-20T17:00:00Z",
  "actual_start_date": "2024-01-15T09:15:00Z",
  "actual_end_date": null,
  "status": "in_progress",
  "status_display": "In Progress",
  "priority": "high",
  "priority_display": "High",
  "customer_order_reference": "CUST-001",
  "delivery_date": "2024-01-25",
  "special_instructions": "Handle with care",
  "submitted_at": "2024-01-15T10:35:00Z",
  "gm_approved_at": "2024-01-15T11:00:00Z",
  "gm_approved_by": {
    "id": 3,
    "email": "gm@example.com",
    "first_name": "General",
    "last_name": "Manager"
  },
  "rm_allocated_at": "2024-01-15T11:30:00Z",
  "rm_allocated_by": {
    "id": 4,
    "email": "store@example.com",
    "first_name": "Store",
    "last_name": "Manager"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:30:00Z",
  "status_history": [
    {
      "id": 1,
      "from_status": "draft",
      "to_status": "submitted",
      "changed_by": {
        "id": 1,
        "email": "admin@example.com",
        "first_name": "Admin",
        "last_name": "User"
      },
      "changed_at": "2024-01-15T10:35:00Z",
      "notes": "Initial submission"
    }
  ]
}
```

### 4. Update Manufacturing Order
**PUT/PATCH** `/api/manufacturing-orders/{id}/`

**Request Body (PATCH example):**
```json
{
  "priority": "urgent",
  "delivery_date": "2024-01-22"
}
```

### 5. Change MO Status
**POST** `/api/manufacturing-orders/{id}/change_status/`

**Request Body:**
```json
{
  "status": "gm_approved",
  "notes": "Approved by GM for immediate production"
}
```

### 6. Get Dashboard Statistics
**GET** `/api/manufacturing-orders/dashboard_stats/`

**Response:**
```json
{
  "total": 150,
  "draft": 10,
  "in_progress": 25,
  "completed": 100,
  "overdue": 5,
  "by_priority": {
    "high": 15,
    "medium": 80,
    "low": 55
  }
}
```

### 7. Get Products Dropdown
**GET** `/api/manufacturing-orders/products/`

**Response:**
```json
[
  {
    "id": 1,
    "product_code": "SPRING-001",
    "part_number": "SP001",
    "part_name": "Compression Spring",
    "display_name": "SP001 - Compression Spring",
    "is_active": true
  }
]
```

### 8. Get Supervisors Dropdown
**GET** `/api/manufacturing-orders/supervisors/`

**Response:**
```json
[
  {
    "id": 2,
    "email": "supervisor@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "display_name": "John Doe"
  }
]
```

---

## Purchase Orders API

### 1. List Purchase Orders
**GET** `/api/purchase-orders/`

**Query Parameters:**
- `status`: Filter by status (draft, submitted, gm_approved, gm_created_po, vendor_confirmed, partially_received, completed, cancelled, rejected)
- `material_type`: Filter by material type (coil, sheet)
- `vendor_name`: Filter by vendor ID
- `expected_date`: Filter by expected date (YYYY-MM-DD)
- `start_date`: Filter from date (YYYY-MM-DD)
- `end_date`: Filter to date (YYYY-MM-DD)
- `search`: Search in po_id, rm_code, vendor_name
- `ordering`: Order by field (created_at, expected_date, po_id, total_amount)
- `page`: Page number for pagination

**Response:** Similar structure to MO list with PO-specific fields

### 2. Create Purchase Order
**POST** `/api/purchase-orders/`

**Request Body:**
```json
{
  "rm_code_id": 1,
  "vendor_name_id": 1,
  "quantity_ordered": 500,
  "expected_date": "2024-01-30",
  "unit_price": "25.50",
  "terms_conditions": "Net 30 days",
  "notes": "Urgent requirement"
}
```

### 3. Get Purchase Order Details
**GET** `/api/purchase-orders/{id}/`

**Response:** Detailed PO information with auto-populated material and vendor details

### 4. Change PO Status
**POST** `/api/purchase-orders/{id}/change_status/`

**Request Body:**
```json
{
  "status": "gm_approved",
  "notes": "Approved by GM"
}
```

**For rejection:**
```json
{
  "status": "rejected",
  "rejection_reason": "Price too high",
  "notes": "Please negotiate better price"
}
```

### 5. Get Dashboard Statistics
**GET** `/api/purchase-orders/dashboard_stats/`

**Response:**
```json
{
  "total": 75,
  "draft": 5,
  "gm_approved": 10,
  "completed": 50,
  "rejected": 3,
  "overdue": 2,
  "total_value": 125000.50
}
```

### 6. Get Raw Materials Dropdown
**GET** `/api/purchase-orders/raw_materials/`

**Response:**
```json
[
  {
    "id": 1,
    "product_code": "RM-STEEL-001",
    "material_name": "spring",
    "material_type": "coil",
    "grade": "EN42J",
    "display_name": "RM-STEEL-001 - Spring Steel EN42J - Coil (⌀2.5mm, 100kg)"
  }
]
```

### 7. Get Vendors Dropdown
**GET** `/api/purchase-orders/vendors/`

**Query Parameters:**
- `vendor_type`: Filter by vendor type (rm_vendor, outsource_vendor)

**Response:**
```json
[
  {
    "id": 1,
    "name": "Steel Suppliers Ltd",
    "vendor_type": "rm_vendor",
    "is_active": true
  }
]
```

### 8. Get Material Details for Auto-population
**GET** `/api/purchase-orders/material_details/?material_id=1`

**Response:**
```json
{
  "id": 1,
  "product_code": "RM-STEEL-001",
  "material_name": "spring",
  "material_name_display": "Spring Steel",
  "material_type": "coil",
  "material_type_display": "Coil",
  "grade": "EN42J",
  "wire_diameter_mm": "2.500",
  "weight_kg": "100.000",
  "thickness_mm": null,
  "quantity": null
}
```

### 9. Get Vendor Details for Auto-population
**GET** `/api/purchase-orders/vendor_details/?vendor_id=1`

**Response:**
```json
{
  "id": 1,
  "name": "Steel Suppliers Ltd",
  "vendor_type": "rm_vendor",
  "vendor_type_display": "RM Vendor",
  "gst_no": "22AAAAA0000A1Z5",
  "address": "123 Industrial Area, Mumbai",
  "contact_no": "+91-9876543210",
  "email": "contact@steelsuppliers.com",
  "contact_person": "Mr. Sharma",
  "is_active": true
}
```

---

## Error Responses

All endpoints return appropriate HTTP status codes and error messages:

**400 Bad Request:**
```json
{
  "error": "Status is required"
}
```

**404 Not Found:**
```json
{
  "error": "Material not found"
}
```

**Validation Errors:**
```json
{
  "product_code_id": ["This field is required."],
  "quantity": ["Ensure this value is greater than 0."]
}
```

---

## Frontend Integration Tips

1. **Auto-population**: When user selects a product in MO form, fetch product details and auto-populate material fields
2. **Status Management**: Use the change_status endpoints for workflow management
3. **Dropdown Data**: Cache dropdown data (products, vendors, etc.) for better performance
4. **Filtering**: Implement advanced filtering using the query parameters
5. **Pagination**: Handle pagination for large datasets
6. **Real-time Updates**: Consider implementing WebSocket connections for real-time status updates
7. **Dashboard**: Use the dashboard_stats endpoints for creating summary widgets

## Example Frontend Form Structure

### Manufacturing Order Form
```javascript
const moForm = {
  product_code_id: null,        // Dropdown selection
  quantity: 0,                  // Number input
  assigned_supervisor_id: null, // Dropdown selection
  shift: '',                    // Radio buttons or dropdown
  planned_start_date: '',       // DateTime picker
  planned_end_date: '',         // DateTime picker
  priority: 'medium',           // Dropdown with default
  delivery_date: '',            // Date picker
  customer_order_reference: '', // Text input
  special_instructions: ''      // Textarea
}
```

### Purchase Order Form
```javascript
const poForm = {
  rm_code_id: null,       // Dropdown selection
  vendor_name_id: null,   // Dropdown selection
  quantity_ordered: 0,    // Number input
  expected_date: '',      // Date picker
  unit_price: 0,          // Number input with decimal
  terms_conditions: '',   // Textarea
  notes: ''               // Textarea
}
```
