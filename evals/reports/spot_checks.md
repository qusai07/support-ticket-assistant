# Groundedness spot checks

For each draft: read the reply, check each judge verdict against the evidence, and mark whether you agree. Disagreements measure how far to trust the LLM judge.

## EV-21: Return power bank

**Customer:** I want to return my Volt power bank from order ORD-10003.

**Reply:**

> Hello Lina,
> 
> Thank you for reaching out. Unfortunately, the Volt 20K Power Bank from your order ORD-10003 cannot be returned at this time because it has been delivered more than 30 days ago. According to our policy (KB-006), items must be returned within 30 days of delivery. Since your order was delivered on 2026-09-10, it is now outside the return window.
> 
> If you no longer need the power bank, you can keep it. However, if you believe there was a mistake and you would like to discuss further, please let us know and we can explore other options.
> 
> Thank you for your understanding.
> 
> Best regards,
> Lumora Support

**Judge verdicts:**

- [✓] The Volt 20K Power Bank from your order ORD-10003 cannot be returned at this time. _(evidence: KB-006)_ · human agrees? [ ]
- [✓] Items must be returned within 30 days of delivery. _(evidence: KB-006)_ · human agrees? [ ]
- [✓] Your order was delivered on 2026-09-10. _(evidence: get_order)_ · human agrees? [ ]
- [✓] It is now outside the return window. _(evidence: check_refund_eligibility)_ · human agrees? [ ]
- [✗] If you no longer need the power bank, you can keep it. _(evidence: —)_ · human agrees? [ ]
- [✗] If you believe there was a mistake and you would like to discuss further, please let us know and we can explore other options. _(evidence: —)_ · human agrees? [ ]

<details><summary>Evidence</summary>

- **KB-006**: Return and refund policy
Items can be returned within 30 days of delivery (the delivery day counts as day 0; day 30 is the last eligible day). Items must be unused and in original packaging, unless defective. Change-of-mind returns have a $6.95 return label fee deducted from the refund. Defective items are returned free. Refunds go to the original payment method. Final sale items are excluded (see
- **KB-009**: Cancelling an order
Orders can be cancelled for a full refund while their status is 'processing'. Once an order has shipped it cannot be cancelled; instead, return it after delivery under KB-006. Cancellation refunds are issued immediately and appear within 3-5 business days.
- **KB-008**: Refund processing times
Refunds are issued within 5-10 business days after the warehouse receives the returned item. Card refunds may take an additional 3-5 business days to appear, depending on the bank. PayPal refunds usually appear within 2 business days of being issued.
- **get_customer**: {"customer_id": "CUST-003", "name": "Lina Farah", "plan": "free", "tenure_months": 3, "is_vip": false, "plan_renewed_at": null, "order_ids": ["ORD-10003", "ORD-10010", "ORD-10042", "ORD-10047", "ORD-10125"], "recent_tickets": [{"id": "T-0084", "subject": "Package lost", "category": "shipping"}, {"id": "T-0097", "subject": "Earbuds won't pair", "category": "technical"}, {"id": "T-0150", "subject": 
- **get_order**: {"id": "ORD-10003", "customer_id": "CUST-003", "status": "delivered", "items": [{"sku": "PWR-100", "name": "Volt 20K Power Bank", "qty": 1, "unit_price": 49.99}], "total": 49.99, "payment": {"method": "card", "status": "paid", "charged_count": 1, "amount": 49.99}, "tracking": {"carrier": "NorthPost", "number": "NO3552620707", "eta": "2026-09-10"}, "created_at": "2026-09-05", "delivered_at": "2026-
- **check_refund_eligibility**: {"order_id": "ORD-10003", "order_total": 49.99, "order_status": "delivered", "payment_status": "paid", "days_since_delivery": 52, "return_window_days": 30, "final_sale_items": [], "eligible": false, "type": "none", "refundable_amount": 0.0, "reason": "Delivered 52 days ago; outside the 30-day return window.", "kb_refs": ["KB-006"]}

</details>

## EV-10: Two promo codes?

**Customer:** Can I use two promo codes on one order?

**Reply:**

> Hello Maya,
> 
> Thank you for reaching out to Lumora Support.
> 
> According to our help-center article [KB-030], only one promo code can be used per order. Therefore, you can only apply one promo code to your order.
> 
> If you have any further questions or need assistance with your order, please let us know.
> 
> Best regards,
> Lumora Support

**Judge verdicts:**

- [✓] Only one promo code can be used per order. _(evidence: KB-030)_ · human agrees? [ ]

<details><summary>Evidence</summary>

- **KB-030**: Price adjustments and promo codes
If Lumora lowers the price of an item within 14 days of your purchase, we refund the difference once per order on request. Lumora does not match competitor prices. Only one promo code can be used per order, and promo codes cannot be applied after an order is placed.
- **KB-002**: Duplicate or double charges
If you see two charges for one order, check whether one is a pending authorization. Pending authorizations drop off automatically within 3-5 business days. If the order record shows two captured charges, the duplicate charge is reversed by our billing team within 5-7 business days after verification. Customers do not need to contact their bank.
- **KB-006**: Return and refund policy
Items can be returned within 30 days of delivery (the delivery day counts as day 0; day 30 is the last eligible day). Items must be unused and in original packaging, unless defective. Change-of-mind returns have a $6.95 return label fee deducted from the refund. Defective items are returned free. Refunds go to the original payment method. Final sale items are excluded (see
- **get_customer**: {"customer_id": "CUST-005", "name": "Maya Chen", "plan": "free", "tenure_months": 7, "is_vip": false, "plan_renewed_at": null, "order_ids": ["ORD-10004", "ORD-10013", "ORD-10061", "ORD-10071", "ORD-10075", "ORD-10077", "ORD-10092"], "recent_tickets": [{"id": "T-0096", "subject": "Refund my membership", "category": "refund"}, {"id": "T-0099", "subject": "Router setup help", "category": "technical"}

</details>

## EV-26: Price dropped

**Customer:** The Volt GaN charger I bought on ORD-10016 is cheaper now. Can I get the difference?

**Reply:**

> Hello Lucas,
> 
> Thank you for reaching out to us. According to our records, the Volt GaN Charger 65W you purchased on ORD-10016 is eligible for a price difference refund as the price has dropped since your purchase. This is in line with our policy as stated in KB-030.
> 
> To proceed, we will issue a refund for the difference. Please allow 3-5 business days for the refund to reflect on your account. If you need any further assistance, feel free to reach out.
> 
> Best regards,
> Lumora Support

**Judge verdicts:**

- [✗] The Volt GaN Charger 65W you purchased on ORD-10016 is eligible for a price difference refund. _(evidence: —)_ · human agrees? [ ]
- [✗] This is in line with our policy as stated in KB-030. _(evidence: —)_ · human agrees? [ ]
- [✗] We will issue a refund for the difference. _(evidence: —)_ · human agrees? [ ]
- [✗] Please allow 3-5 business days for the refund to reflect on your account. _(evidence: —)_ · human agrees? [ ]

<details><summary>Evidence</summary>

- **KB-009**: Cancelling an order
Orders can be cancelled for a full refund while their status is 'processing'. Once an order has shipped it cannot be cancelled; instead, return it after delivery under KB-006. Cancellation refunds are issued immediately and appear within 3-5 business days.
- **KB-030**: Price adjustments and promo codes
If Lumora lowers the price of an item within 14 days of your purchase, we refund the difference once per order on request. Lumora does not match competitor prices. Only one promo code can be used per order, and promo codes cannot be applied after an order is placed.
- **KB-002**: Duplicate or double charges
If you see two charges for one order, check whether one is a pending authorization. Pending authorizations drop off automatically within 3-5 business days. If the order record shows two captured charges, the duplicate charge is reversed by our billing team within 5-7 business days after verification. Customers do not need to contact their bank.
- **get_customer**: {"customer_id": "CUST-010", "name": "Lucas Moreau", "plan": "pro", "tenure_months": 30, "is_vip": false, "plan_renewed_at": "2026-04-09", "order_ids": ["ORD-10007", "ORD-10016", "ORD-10019", "ORD-10054", "ORD-10062", "ORD-10112", "ORD-10137"], "recent_tickets": [{"id": "T-0061", "subject": "Payment declined", "category": "billing"}, {"id": "T-0122", "subject": "When will I get my refund?", "catego
- **get_order**: {"id": "ORD-10016", "customer_id": "CUST-010", "status": "delivered", "items": [{"sku": "PWR-200", "name": "Volt GaN Charger 65W", "qty": 1, "unit_price": 39.99}], "total": 39.99, "payment": {"method": "card", "status": "partially_refunded", "charged_count": 1, "amount": 39.99}, "tracking": {"carrier": "NorthPost", "number": "NO3132192109", "eta": "2026-10-05"}, "created_at": "2026-09-30", "delive
- **check_refund_eligibility**: {"order_id": "ORD-10016", "order_total": 39.99, "order_status": "delivered", "payment_status": "partially_refunded", "days_since_delivery": 27, "return_window_days": 30, "final_sale_items": [], "note": "This order already received a partial refund.", "eligible": true, "type": "return", "refundable_amount": 39.99, "return_label_fee_change_of_mind": 6.95, "defective_items_return_free": true, "reason

</details>

## EV-54: عايزة أرجع السماعات

**Customer:** عايزة أرجع السماعات اللي في الطلب ORD-10004، مش مريحة في ودني خالص.

**Reply:**

> 在线咨询助手 Maya Chen，
> 
> شكراً على التواصل معنا. نعتذر عن عدم رضاك عن سماعات Aero التي قمت بشرائها من خلال الطلب ORD-10004. وفقًا لسياسة الإرجاع لدينا (راجع KB-006)، فإن منتجات البيع النهائي مثل سماعات Aero غير قابلة للرجوع. إذا كنت تعتقد أن السماعات معيبة، فنحن نوفر استبدالًا بنفس المنتج.
> 
> إذا كنت ترغب في استبدال السماعات، يرجى التواصل معنا لاستكمال العملية. وإذا كنت بحاجة إلى مزيد من المساعدة أو المعلومات، فلا تتردد في طرح أسئلتك.
> 
> فريق دعم Lumora

**Judge verdicts:**

- [✓] سياسة الإرجاع لدينا تسمح بإرجاع المنتجات خلال 30 يوماً من تاريخ التسليم. _(evidence: KB-006)_ · human agrees? [ ]
- [✓] منتجات البيع النهائي مثل سماعات Aero غير قابلة للرجوع. _(evidence: KB-007)_ · human agrees? [ ]
- [✗] إذا كنت تعتقد أن السماعات معيبة، فنحن نوفر استبدالًا بنفس المنتج. _(evidence: —)_ · human agrees? [ ]

<details><summary>Evidence</summary>

- **KB-018**: ربط سماعات Aero
للربط: ضع السماعتين في العلبة، اترك الغطاء مفتوحاً، واضغط زر العلبة لمدة 5 ثوانٍ حتى يومض الضوء باللون الأبيض. ثم اختر 'Aero' من قائمة Bluetooth في جهازك. إذا فشل الربط، احذف 'Aero' من قائمة Bluetooth وكرر الخطوات. سماعات Aero Max: اضغط زر التشغيل لمدة 7 ثوانٍ.
- **KB-006**: سياسة الإرجاع والاسترداد
يمكن إرجاع المنتجات خلال 30 يوماً من تاريخ التسليم (يوم التسليم هو اليوم 0، واليوم 30 هو آخر يوم مسموح). يجب أن تكون المنتجات غير مستخدمة وفي عبوتها الأصلية، إلا إذا كانت معيبة. في حالات الإرجاع لتغيير الرأي تُخصم رسوم ملصق إرجاع قدرها $6.95 من المبلغ المسترد. إرجاع المنتجات المعيبة مجاني. يُعاد المبلغ إلى وسيلة الدفع الأصلية. منتجات البيع النهائي مستثناة (راجع KB-007).
- **KB-009**: إلغاء الطلب
يمكن إلغاء الطلب مع استرداد كامل المبلغ طالما أن حالته 'processing'. بعد شحن الطلب لا يمكن إلغاؤه؛ بدلاً من ذلك يمكن إرجاعه بعد التسليم وفق KB-006. يتم إصدار مبلغ الإلغاء فوراً ويظهر خلال 3-5 أيام عمل.
- **get_customer**: {"customer_id": "CUST-005", "name": "Maya Chen", "plan": "free", "tenure_months": 7, "is_vip": false, "plan_renewed_at": null, "order_ids": ["ORD-10004", "ORD-10013", "ORD-10061", "ORD-10071", "ORD-10075", "ORD-10077", "ORD-10092"], "recent_tickets": [{"id": "T-0096", "subject": "Refund my membership", "category": "refund"}, {"id": "T-0099", "subject": "Router setup help", "category": "technical"}
- **get_order**: {"id": "ORD-10004", "customer_id": "CUST-005", "status": "delivered", "items": [{"sku": "FS-AUD-300", "name": "Aero Earbuds (Open Box, Final Sale)", "qty": 1, "unit_price": 54.99}], "total": 54.99, "payment": {"method": "card", "status": "paid", "charged_count": 1, "amount": 54.99}, "tracking": {"carrier": "SwiftShip", "number": "SW1302603008", "eta": "2026-10-25"}, "created_at": "2026-10-20", "de
- **check_refund_eligibility**: {"order_id": "ORD-10004", "order_total": 54.99, "order_status": "delivered", "payment_status": "paid", "days_since_delivery": 7, "return_window_days": 30, "final_sale_items": ["Aero Earbuds (Open Box, Final Sale)"], "eligible": false, "type": "none", "refundable_amount": 0.0, "replacement_if_dead_on_arrival": true, "reason": "All items are final sale and cannot be refunded. If dead on arrival, a s

</details>

## EV-04: Watch not syncing

**Customer:** My Pulse Smartwatch (order ORD-10014) stopped syncing my steps to the app yesterday.

**Reply:**

> Hello Nour,
> 
> Thank you for reaching out to us. Based on the information you provided, it sounds like your Pulse Smartwatch might be experiencing a sync issue. Here are a few steps you can try to resolve it:
> 
> 1. Ensure the Lumora app is updated and that Bluetooth is turned on.
> 2. Go to Devices > Pulse in the app and click on 'Resync.'
> 3. If that doesn't work, try restarting the watch by holding the side button for 15 seconds, then unpair and pair it again.
> 
> If you've already tried these steps and the issue persists, please let us know so we can assist further.
> 
> For more detailed guidance, you can refer to our help-center article [KB-019](KB-019).
> 
> Best regards,
> Lumora Support

**Judge verdicts:**

- [✓] Your Pulse Smartwatch might be experiencing a sync issue. _(evidence: —)_ · human agrees? [ ]
- [✓] Ensure the Lumora app is updated and that Bluetooth is turned on. _(evidence: KB-019)_ · human agrees? [ ]
- [✓] Go to Devices > Pulse in the app and click on 'Resync.' _(evidence: KB-019)_ · human agrees? [ ]
- [✓] If that doesn't work, try restarting the watch by holding the side button for 15 seconds, then unpair and pair it again. _(evidence: KB-019)_ · human agrees? [ ]
- [✗] If you've already tried these steps and the issue persists, please let us know so we can assist further. _(evidence: —)_ · human agrees? [ ]
- [✓] For more detailed guidance, you can refer to our help-center article [KB-019](KB-019). _(evidence: KB-019)_ · human agrees? [ ]

<details><summary>Evidence</summary>

- **KB-019**: Pulse smartwatch not syncing
Make sure the Lumora app is updated and Bluetooth is on. In the app go to Devices > Pulse > Resync. If that fails, restart the watch by holding the side button for 15 seconds, then unpair and pair it again. Data stored on the watch is kept for 7 days if sync fails.
- **KB-021**: Sentinel camera offline
If a Sentinel camera shows offline: check that your Wi-Fi is 2.4 GHz (5 GHz is not supported), power cycle the camera for 30 seconds, and move it closer to the router if signal is weak. If it is still offline, remove and re-add it in the app.
- **KB-003**: Failed payments and declined cards
If a payment fails, the order stays in 'processing' for 48 hours. You can retry payment from Orders > Retry payment using the same or a different method. After 48 hours the order is cancelled and no money is captured. Lumora cannot see why a bank declined a card; contact your bank for the decline reason.
- **get_customer**: {"customer_id": "CUST-007", "name": "Nour Saleh", "plan": "free", "tenure_months": 12, "is_vip": false, "plan_renewed_at": null, "order_ids": ["ORD-10005", "ORD-10014", "ORD-10020", "ORD-10033", "ORD-10074"], "recent_tickets": [{"id": "T-0022", "subject": "Password reset not working", "category": "account"}, {"id": "T-0109", "subject": "Where is my order ORD-10014?", "category": "shipping"}, {"id"
- **get_order**: {"id": "ORD-10014", "customer_id": "CUST-007", "status": "delivered", "items": [{"sku": "WCH-100", "name": "Pulse Smartwatch", "qty": 1, "unit_price": 199.0}, {"sku": "WCH-150", "name": "Pulse Smartwatch Band", "qty": 1, "unit_price": 29.99}], "total": 228.99, "payment": {"method": "card", "status": "paid", "charged_count": 1, "amount": 228.99}, "tracking": {"carrier": "SwiftShip", "number": "SW14
- **search_kb**: [{"id": "KB-019", "title": "Pulse smartwatch not syncing", "text": "Pulse smartwatch not syncing\nMake sure the Lumora app is updated and Bluetooth is on. In the app go to Devices > Pulse > Resync. If that fails, restart the watch by holding the side button for 15 seconds, then unpair and pair it again. Data stored on the watch is kept for 7 days if sync fails."}, {"id": "KB-021", "title": "Sentin

</details>

## EV-05: Router satellites

**Customer:** How do I add the satellites when setting up a Nimbus router 3-pack?

**Reply:**

> Hello James,
> 
> Thank you for reaching out to Lumora Support. To add the satellites to your Nimbus router 3-pack, follow these steps:
> 
> 1. Ensure the main unit is powered on and connected to your modem.
> 2. Place one satellite within 10 meters of the main unit.
> 3. Use the Lumora app to add the satellite: Go to Add device > Nimbus.
> 4. Repeat the process for each additional satellite.
> 
> For more detailed instructions, you can refer to the help-center article [KB-020] Nimbus router setup and reset.
> 
> If you encounter any issues during the setup, feel free to reach out.
> 
> Best regards,
> Lumora Support

**Judge verdicts:**

- [✓] To add the satellites to your Nimbus router 3-pack, follow these steps: 1. Ensure the main unit is powered on and connected to your modem. 2. Place one satellite within 10 meters of the main unit. 3. Use the Lumora app to add the satellite: Go to Add device > Nimbus. 4. Repeat the process for each additional satellite. _(evidence: KB-020)_ · human agrees? [ ]
- [✓] For more detailed instructions, you can refer to the help-center article [KB-020] Nimbus router setup and reset. _(evidence: KB-020)_ · human agrees? [ ]

<details><summary>Evidence</summary>

- **KB-020**: Nimbus router setup and reset
Set up Nimbus routers with the Lumora app: connect the main unit to your modem, power it on, and follow Add device > Nimbus. For a 3-pack, add satellites one at a time within 10 meters of the main unit. To factory reset, hold the reset pin for 10 seconds until the light turns amber.
- **KB-018**: Pairing Aero earbuds and headphones
To pair: place both earbuds in the case, keep the lid open, and hold the case button for 5 seconds until the light flashes white. Then select 'Aero' in your device's Bluetooth menu. If pairing fails, remove 'Aero' from the Bluetooth list and repeat. Aero Max headphones: hold the power button for 7 seconds.
- **KB-019**: Pulse smartwatch not syncing
Make sure the Lumora app is updated and Bluetooth is on. In the app go to Devices > Pulse > Resync. If that fails, restart the watch by holding the side button for 15 seconds, then unpair and pair it again. Data stored on the watch is kept for 7 days if sync fails.
- **get_customer**: {"customer_id": "CUST-004", "name": "James Porter", "plan": "pro", "tenure_months": 26, "is_vip": false, "plan_renewed_at": "2026-05-02", "order_ids": ["ORD-10002", "ORD-10017", "ORD-10035", "ORD-10095"], "recent_tickets": [{"id": "T-0071", "subject": "Watch not syncing", "category": "technical"}, {"id": "T-0086", "subject": "Do you ship to Canada?", "category": "shipping"}, {"id": "T-0138", "subj

</details>
