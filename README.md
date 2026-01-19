
## Integration Flow

1.  **Product Configuration**:
    *   Go to the product form in the backend.
    *   Enable the checkbox **"انشاء امر تصنيع تلقائي من pos"** (Trigger Manufacturing from POS).
    *   Ensure the product has a valid Bill of Materials (BoM) of type "Manufacture this product".

2.  **POS Session**:
    *   Cashier adds the configured product to the POS cart.

3.  **Pre-Payment Validation**:
    *   Before payment is processed, the system validates that:
        *   The product has a valid BoM.

4.  **Manufacturing Order Creation**:
    *   Upon successful payment, the system automatically creates a **Manufacturing Order (MO)** for the sold product.
    *   The MO is linked to the POS order via the `pos_order_id` field.
    *   The MO is created in the **Confirmed** state.