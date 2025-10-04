# RM Store Dashboard API Guide

This guide provides comprehensive documentation for the RM Store user dashboard functionality, including all API endpoints and usage examples.

## Overview

The RM Store dashboard allows users with the `rm_store` role to:
- View all products with their stock balances
- Create new products
- Update product information
- Manage stock balances using internal product codes
- Bulk update stock quantities

## Authentication & Permissions

All endpoints require:
1. **Authentication**: Valid JWT token
2. **Role Permission**: User must have `rm_store` role assigned

### Headers Required
```
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

## API Endpoints

### 1. Dashboard Overview

#### Get Dashboard Statistics
```http
GET /api/inventory/dashboard/stats/
```

**Response:**
```json
{
  "total_products": 150,
  "products_with_stock": 120,
  "products_out_of_stock": 20,
  "products_no_stock_record": 10,
  "total_stock_records": 140
}
```

#### Get Products Dashboard
```http
GET /api/inventory/products/dashboard/
```

**Response:**
```json
[
  {
    "id": 1,
    "internal_product_code": "ABC123",
    "product_code": "SPR-001",
    "product_type": "spring",
    "product_type_display": "Spring",
    "spring_type": "tension",
    "spring_type_display": "TENSION SPRING",
    "material_name": "Steel Wire",
    "material_type_display": "Coil",
    "stock_info": {
      "available_quantity": 100,
      "last_updated": "2024-01-15T10:30:00Z",
      "stock_status": "in_stock"
    }
  },
  {
    "id": 2,
    "internal_product_code": "DEF456",
    "product_code": "SPR-002",
    "product_type": "spring",
    "product_type_display": "Spring",
    "spring_type": "compression",
    "spring_type_display": "COMPRESSION SPRING",
    "material_name": "Stainless Steel",
    "material_type_display": "Sheet",
    "stock_info": {
      "available_quantity": 0,
      "last_updated": null,
      "stock_status": "no_stock_record"
    }
  }
]
```

### 2. Product Management

#### List Products
```http
GET /api/inventory/products/
```

**Query Parameters:**
- `product_type`: spring, press_component
- `spring_type`: tension, compression, etc.
- `search`: searches in product_code, internal_product_code, material name
- `ordering`: product_code, internal_product_code, created_at (add - for descending)
- `page`: page number for pagination

**Example:**
```http
GET /api/inventory/products/?search=spring&product_type=spring&ordering=-created_at
```

#### Create Product
```http
POST /api/inventory/products/
```

**Request Body:**
```json
{
  "internal_product_code": "ABC123",
  "product_code": "SPR-001",
  "product_type": "spring",
  "spring_type": "tension",
  "material": 1
}
```

**Response:**
```json
{
  "id": 1,
  "internal_product_code": "ABC123",
  "product_code": "SPR-001",
  "product_type": "spring",
  "spring_type": "tension",
  "material": 1
}
```

#### Update Product
```http
PUT /api/inventory/products/{id}/
```

**Request Body:**
```json
{
  "internal_product_code": "ABC123",
  "product_code": "SPR-001-UPDATED",
  "product_type": "spring",
  "spring_type": "compression",
  "material": 2
}
```

#### Get Product Details
```http
GET /api/inventory/products/{id}/
```

#### Delete Product
```http
DELETE /api/inventory/products/{id}/
```

### 3. Stock Balance Management

#### Update Stock by Internal Product Code (Single)
```http
POST /api/inventory/stock-balances/update_by_product_code/
```

**Request Body:**
```json
{
  "internal_product_code": "ABC123",
  "available_quantity": 100
}
```

**Response:**
```json
{
  "message": "Stock balance updated successfully",
  "internal_product_code": "ABC123",
  "available_quantity": 100,
  "created": false,
  "last_updated": "2024-01-15T10:30:00Z"
}
```

#### Bulk Update Stock Balances
```http
POST /api/inventory/stock-balances/bulk_update/
```

**Request Body:**
```json
[
  {
    "internal_product_code": "ABC123",
    "available_quantity": 100
  },
  {
    "internal_product_code": "DEF456",
    "available_quantity": 50
  },
  {
    "internal_product_code": "GHI789",
    "available_quantity": 200
  }
]
```

**Response:**
```json
{
  "message": "Successfully updated 3 stock records",
  "updated_records": [
    {
      "internal_product_code": "ABC123",
      "available_quantity": 100,
      "created": false,
      "last_updated": "2024-01-15T10:30:00Z"
    },
    {
      "internal_product_code": "DEF456",
      "available_quantity": 50,
      "created": true,
      "last_updated": "2024-01-15T10:30:00Z"
    },
    {
      "internal_product_code": "GHI789",
      "available_quantity": 200,
      "created": false,
      "last_updated": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### List Stock Balances
```http
GET /api/inventory/stock-balances/
```

**Query Parameters:**
- `search`: searches in product codes
- `ordering`: available_quantity, last_updated (add - for descending)

#### Create Stock Balance
```http
POST /api/inventory/stock-balances/
```

**Request Body:**
```json
{
  "product": 1,
  "available_quantity": 100
}
```

Or using internal product code:
```json
{
  "product_internal_code": "ABC123",
  "available_quantity": 100
}
```

### 4. Raw Materials (for Product Creation)

#### Get Raw Materials Dropdown
```http
GET /api/inventory/raw-materials/dropdown/
```

**Response:**
```json
[
  {
    "id": 1,
    "material_code": "RM001",
    "material_name": "Steel Wire",
    "material_type": "coil",
    "display_name": "RM001 - Steel Wire"
  },
  {
    "id": 2,
    "material_code": "RM002",
    "material_name": "Stainless Steel Sheet",
    "material_type": "sheet",
    "display_name": "RM002 - Stainless Steel Sheet"
  }
]
```

#### List Raw Materials
```http
GET /api/inventory/raw-materials/
```

**Query Parameters:**
- `material_type`: coil, sheet
- `material_name`: specific material name
- `search`: searches in material_code, material_name, grade

### 5. Dropdown Data

#### Get Products Dropdown
```http
GET /api/inventory/products/dropdown/
```

**Response:**
```json
[
  {
    "id": 1,
    "internal_product_code": "ABC123",
    "product_code": "SPR-001",
    "display_name": "ABC123 - SPR-001"
  },
  {
    "id": 2,
    "internal_product_code": "DEF456",
    "product_code": "SPR-002",
    "display_name": "DEF456 - SPR-002"
  }
]
```

## Frontend Integration Examples

### JavaScript/React Examples

#### 1. Fetch Dashboard Data
```javascript
const fetchDashboardData = async () => {
  try {
    const response = await fetch('/api/inventory/products/dashboard/', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching dashboard data:', error);
  }
};
```

#### 2. Update Stock Balance
```javascript
const updateStockBalance = async (internalProductCode, quantity) => {
  try {
    const response = await fetch('/api/inventory/stock-balances/update_by_product_code/', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        internal_product_code: internalProductCode,
        available_quantity: quantity
      })
    });
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error updating stock balance:', error);
  }
};
```

#### 3. Create New Product
```javascript
const createProduct = async (productData) => {
  try {
    const response = await fetch('/api/inventory/products/', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(productData)
    });
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error creating product:', error);
  }
};
```

#### 4. Bulk Update Stock Balances
```javascript
const bulkUpdateStockBalances = async (stockUpdates) => {
  try {
    const response = await fetch('/api/inventory/stock-balances/bulk_update/', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(stockUpdates)
    });
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error bulk updating stock balances:', error);
  }
};
```

## Error Handling

### Common Error Responses

#### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

#### 403 Forbidden (Not RM Store User)
```json
{
  "detail": "You do not have permission to perform this action."
}
```

#### 400 Bad Request (Validation Error)
```json
{
  "internal_product_code": ["Product with this internal code does not exist."],
  "available_quantity": ["Available quantity cannot be negative."]
}
```

#### 404 Not Found
```json
{
  "detail": "Not found."
}
```

## Stock Status Values

The `stock_status` field in dashboard responses can have these values:
- `in_stock`: Product has available quantity > 0
- `out_of_stock`: Product has available quantity = 0
- `no_stock_record`: No stock balance record exists for this product
- `error`: Error occurred while fetching stock information

## Best Practices

1. **Always validate internal_product_code** before making stock updates
2. **Use bulk updates** when updating multiple stock balances for better performance
3. **Handle errors gracefully** and provide user feedback
4. **Cache dropdown data** to reduce API calls
5. **Implement pagination** for large product lists
6. **Use search and filtering** to help users find products quickly

## Rate Limiting

- No specific rate limits are currently implemented
- However, use bulk operations when possible for better performance

## Support

For technical support or questions about the RM Store API, please contact the development team.
