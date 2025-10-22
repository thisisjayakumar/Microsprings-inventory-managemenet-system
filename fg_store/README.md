# FG Store & Dispatch Dashboard - Implementation Guide

## Overview

The FG Store & Dispatch Dashboard is a comprehensive solution for managing finished goods inventory, dispatch operations, and stock levels in the Microsprings ERP system. This implementation provides real-time visibility into stock levels, streamlined dispatch workflows, and complete audit trails.

## Features Implemented

### 1. FG Stock Level Dashboard
- **Real-time stock visibility** with batch-level tracking
- **Advanced filtering** by product, customer, batch ID, and status
- **Stock level indicators** with color-coded alerts (low stock, normal, high)
- **Location tracking** for physical inventory management
- **Sortable columns** for efficient data navigation

### 2. MO List (Pending Dispatch)
- **Manufacturing order management** with dispatch status tracking
- **Customer and priority filtering** for efficient order processing
- **Delivery date monitoring** with overdue indicators
- **Dispatch percentage tracking** for progress visibility
- **Quick dispatch actions** for streamlined operations

### 3. Dispatch Workflow
- **Two-step dispatch process**:
  1. **Dispatch Entry**: Select batches and specify quantities
  2. **Supervisor Confirmation**: Physical verification and confirmation
- **Quantity validation** to prevent overselling
- **Batch-level dispatch** with partial dispatch support
- **Automatic status updates** for MOs and batches

### 4. Transactions Log
- **Complete audit trail** for all dispatch operations
- **Advanced filtering** by date range, MO ID, batch ID, supervisor
- **Export functionality** (CSV/PDF) for reporting
- **Real-time updates** with transaction status tracking

### 5. Stock Alerts
- **Proactive notifications** for low stock, expiring batches, and overstock
- **Configurable thresholds** per product
- **Severity levels** (Low, Medium, High, Critical)
- **Alert management** with activation/deactivation controls

## Technical Implementation

### Backend (Django)

#### Models Created
1. **DispatchBatch**: Tracks finished goods batches ready for dispatch
2. **DispatchTransaction**: Records all dispatch operations with audit trail
3. **DispatchOrder**: Groups multiple dispatch transactions for a single MO
4. **FGStockAlert**: Manages proactive stock level notifications

#### API Endpoints
- `GET /api/fg-store/dashboard/stock_levels/` - FG Stock Level data
- `GET /api/fg-store/dashboard/pending_dispatch_mos/` - MO List data
- `GET /api/fg-store/dashboard/transactions_log/` - Transactions log
- `POST /api/fg-store/dispatch-transactions/` - Create dispatch transaction
- `POST /api/fg-store/dispatch-transactions/{id}/confirm/` - Confirm dispatch
- `GET /api/fg-store/dashboard/validate_dispatch/` - Validate dispatch quantities

#### Security Features
- **Role-based access control** (FG Store role required)
- **Data validation** at model and API levels
- **Audit trails** for all operations
- **Idempotency** for safe retries

### Frontend (Next.js)

#### Components Created
1. **FGStockLevel.js** - Stock level dashboard with filtering and sorting
2. **MOList.js** - Manufacturing orders list with dispatch actions
3. **DispatchModal.js** - Dispatch entry form with batch selection
4. **ConfirmDispatchModal.js** - Supervisor confirmation with verification checklist
5. **TransactionsLog.js** - Complete transaction history with export
6. **StockAlerts.js** - Alert management and configuration

#### Key Features
- **Responsive design** for desktop and tablet use
- **Real-time updates** with refresh functionality
- **Advanced filtering** and search capabilities
- **Export functionality** for reporting
- **Error handling** with user-friendly messages

## Database Schema

### DispatchBatch
```sql
- batch_id (CharField, unique, auto-generated)
- mo (ForeignKey to ManufacturingOrder)
- production_batch (ForeignKey to Batch)
- product_code (ForeignKey to Product)
- quantity_produced (PositiveInteger)
- quantity_packed (PositiveInteger)
- quantity_dispatched (PositiveInteger)
- loose_stock (PositiveInteger)
- status (CharField with choices)
- location_in_store (CharField)
- packing_date (DateTimeField)
- packing_supervisor (ForeignKey to User)
```

### DispatchTransaction
```sql
- transaction_id (CharField, unique, auto-generated)
- mo (ForeignKey to ManufacturingOrder)
- dispatch_batch (ForeignKey to DispatchBatch)
- customer_c_id (ForeignKey to Customer)
- quantity_dispatched (PositiveInteger)
- dispatch_date (DateTimeField, auto_now_add)
- supervisor_id (ForeignKey to User)
- status (CharField with choices)
- notes (TextField)
- delivery_reference (CharField)
- confirmed_at (DateTimeField)
```

## Workflow Process

### 1. Stock Level View
- Load all available batches with "pending dispatch" status
- Display batch details: batch ID, MO ID, customer, product, quantities
- Filter by product type, customer, batch status, date range

### 2. MO Selection
- FG Store Supervisor selects an MO_ID from the MO List
- System shows all batches linked to the MO
- Customer details, delivery date, and special instructions displayed

### 3. Dispatch Entry
- Input quantities to dispatch for each batch
- System validates quantities against available stock
- Allow partial dispatch per batch
- Update batch status to "pending dispatch"

### 4. Physical Loading Supervision
- Supervisor verification checklist
- Physical quantity confirmation
- Quality and packaging verification
- Documentation review

### 5. Confirm Dispatch
- Supervisor clicks "Confirm Dispatch"
- System performs final validation
- Auto-generate transaction record
- Update batch and MO statuses

### 6. Auto-Update Transactions
- Deduct from FG store inventory
- Record transaction details with supervisor ID
- Update MO status to "dispatched" if fully completed
- Generate audit trail

## API Usage Examples

### Get Stock Levels
```javascript
const response = await fetch('/api/fg-store/dashboard/stock_levels/', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
const stockLevels = await response.json();
```

### Create Dispatch Transaction
```javascript
const transactionData = {
  mo: moId,
  dispatch_batch: batchId,
  customer_c_id: customerId,
  quantity_dispatched: quantity,
  supervisor_id: supervisorId,
  notes: 'Dispatch notes'
};

const response = await fetch('/api/fg-store/dispatch-transactions/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(transactionData)
});
```

### Confirm Dispatch
```javascript
const response = await fetch(`/api/fg-store/dispatch-transactions/${transactionId}/confirm/`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ notes: 'Confirmation notes' })
});
```

## Setup Instructions

### 1. Backend Setup
```bash
# Run migrations
python manage.py makemigrations fg_store
python manage.py migrate

# Create sample data
python manage.py create_fg_store_sample_data

# Create FG Store role and assign to users
python manage.py shell
>>> from authentication.models import Role
>>> role, created = Role.objects.get_or_create(name='fg_store')
>>> # Assign role to users as needed
```

### 2. Frontend Setup
```bash
# The components are already integrated into the existing Next.js app
# Access via: http://localhost:3000/fg-store
```

### 3. User Role Assignment
- Assign `fg_store` role to FG Store Supervisors and Managers
- Ensure users have appropriate permissions for dispatch operations

## Testing

### Backend Tests
```bash
python manage.py test fg_store
```

### Frontend Tests
```bash
npm test -- --testPathPattern=fg-store
```

## Performance Considerations

### Database Optimization
- **Indexes** on frequently queried fields (mo_id, batch_id, customer_c_id, dispatch_date)
- **Select_related/prefetch_related** for foreign key optimization
- **Pagination** for large datasets (default: 50 items per page)

### Caching Strategy
- **Redis caching** for stock levels (5-minute TTL)
- **Query result caching** for frequently accessed data
- **Real-time updates** via WebSocket (future enhancement)

## Security Measures

### Access Control
- **Role-based permissions** (FG Store role required)
- **User authentication** for all operations
- **Supervisor verification** for dispatch confirmations

### Data Validation
- **Quantity validation** against available stock
- **Batch status validation** before dispatch
- **Delivery date constraints** checking

### Audit Trail
- **Complete transaction logging** with user IDs and timestamps
- **Immutable audit records** once confirmed
- **Idempotency tokens** for safe retries

## Future Enhancements

### Phase 1 (Current)
- ✅ Basic dispatch workflow
- ✅ Stock level tracking
- ✅ Transaction logging
- ✅ Stock alerts

### Phase 2 (Planned)
- 🔄 Real-time WebSocket updates
- 🔄 Advanced reporting and analytics
- 🔄 Integration with external shipping systems
- 🔄 Mobile app support

### Phase 3 (Future)
- 📋 AI-powered demand forecasting
- 📋 Automated reorder points
- 📋 Integration with IoT sensors
- 📋 Advanced quality tracking

## Troubleshooting

### Common Issues

1. **Permission Denied**
   - Ensure user has `fg_store` role assigned
   - Check role permissions in Django admin

2. **Dispatch Validation Errors**
   - Verify batch has available quantity
   - Check batch status is not "fully_dispatched"
   - Ensure MO status is "completed"

3. **API Errors**
   - Check authentication token validity
   - Verify request payload format
   - Check server logs for detailed error messages

### Debug Commands
```bash
# Check FG Store data
python manage.py shell
>>> from fg_store.models import DispatchBatch
>>> DispatchBatch.objects.count()

# Check user roles
>>> from authentication.models import UserRole
>>> UserRole.objects.filter(user__email='user@example.com')
```

## Support

For technical support or feature requests:
1. Check the troubleshooting section above
2. Review the API documentation
3. Contact the development team
4. Create an issue in the project repository

## License

This implementation is part of the Microsprings ERP system and follows the same licensing terms as the main project.
