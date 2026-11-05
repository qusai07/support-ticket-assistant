# Groundedness spot checks

For each draft: read the reply, check each judge verdict against the evidence, and mark whether you agree. Disagreements measure how far to trust the LLM judge.

## EV-50: متى يصل طلبي؟

**Customer:** مرحباً، متى سيصل الطلب رقم ORD-10009؟ شكراً

**Reply:**

>  Spokane
> 
> مرحباً، أشكرك على اتصالك بنا. تم شحن طلبك رقم ORD-10009 في 29 أكتوبر 2026 بواسطة شركة ParcelGo، ورقم تتبعه هو PA0857037245. تاريخ التسليم المتوقع هو 4 نوفمبر 2026.
> 
> إذا لم تظهر أي تحديثات في تتبع الطلب بعد، يرجى الانتظار لمدة 24 ساعة أخرى. في حال تأخر الطلب عن هذا التاريخ، يمكن فتح طلب تتبع مع شركة الشحن.
> 
> إذا كنت ترغب في تتبع الطلب بشكل مباشر، يمكنك زيارة الموقع الرسمي لشركة ParcelGo وتسجيل رقم التتبع هناك.
> 
> إذا استمرت مشكلتك أو لديك أي أسئلة أخرى، فلا تتردد في الاتصال بنا مرة أخرى.
> 
> مع خالص التحيات،
> فريق دعم Lumora

**Judge verdicts:**


<details><summary>Evidence</summary>

- **KB-009**: إلغاء الطلب
يمكن إلغاء الطلب مع استرداد كامل المبلغ طالما أن حالته 'processing'. بعد شحن الطلب لا يمكن إلغاؤه؛ بدلاً من ذلك يمكن إرجاعه بعد التسليم وفق KB-006. يتم إصدار مبلغ الإلغاء فوراً ويظهر خلال 3-5 أيام عمل.
- **KB-013**: تتبع الطلب
يُرسل رقم التتبع بالبريد الإلكتروني عند شحن الطلب ويظهر في قسم Orders. قد يستغرق ظهور أول تحديث للتتبع حتى 24 ساعة. تاريخ التسليم المتوقع (ETA) تحدده شركة الشحن.
- **KB-014**: تأخر الشحنات
التأخير من 1 إلى 4 أيام عمل بعد التاريخ المتوقع شائع ويُحل عادة دون أي إجراء. إذا تأخر الطلب 5 أيام عمل أو أكثر عن التاريخ المتوقع، يفتح فريق الدعم طلب تتبع (trace) مع شركة الشحن، ويستغرق ذلك حتى 3 أيام عمل.
- **get_customer**: {"customer_id": "CUST-002", "name": "Omar Khalil", "plan": "pro", "tenure_months": 18, "is_vip": false, "plan_renewed_at": "2026-10-28", "order_ids": ["ORD-10001", "ORD-10009", "ORD-10043", "ORD-10064"], "recent_tickets": [{"id": "T-0057", "subject": "Package lost", "category": "shipping"}, {"id": "T-0098", "subject": "Watch not syncing", "category": "technical"}, {"id": "T-0175", "subject": "Item
- **get_order**: {"id": "ORD-10009", "customer_id": "CUST-002", "status": "shipped", "items": [{"sku": "HOM-200", "name": "Halo Smart Bulb 4-Pack", "qty": 1, "unit_price": 44.99}], "total": 44.99, "payment": {"method": "card", "status": "paid", "charged_count": 1, "amount": 44.99}, "tracking": {"carrier": "ParcelGo", "number": "PA0857037245", "eta": "2026-11-04"}, "created_at": "2026-10-29", "delivered_at": null, 

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


<details><summary>Evidence</summary>

- **KB-030**: Price adjustments and promo codes
If Lumora lowers the price of an item within 14 days of your purchase, we refund the difference once per order on request. Lumora does not match competitor prices. Only one promo code can be used per order, and promo codes cannot be applied after an order is placed.
- **KB-002**: Duplicate or double charges
If you see two charges for one order, check whether one is a pending authorization. Pending authorizations drop off automatically within 3-5 business days. If the order record shows two captured charges, the duplicate charge is reversed by our billing team within 5-7 business days after verification. Customers do not need to contact their bank.
- **KB-006**: Return and refund policy
Items can be returned within 30 days of delivery (the delivery day counts as day 0; day 30 is the last eligible day). Items must be unused and in original packaging, unless defective. Change-of-mind returns have a $6.95 return label fee deducted from the refund. Defective items are returned free. Refunds go to the original payment method. Final sale items are excluded (see
- **get_customer**: {"customer_id": "CUST-005", "name": "Maya Chen", "plan": "free", "tenure_months": 7, "is_vip": false, "plan_renewed_at": null, "order_ids": ["ORD-10004", "ORD-10013", "ORD-10061", "ORD-10071", "ORD-10075", "ORD-10077", "ORD-10092"], "recent_tickets": [{"id": "T-0096", "subject": "Refund my membership", "category": "refund"}, {"id": "T-0099", "subject": "Router setup help", "category": "technical"}

</details>

## EV-40: Where is my package

**Customer:** I ordered something last week and it hasn't arrived. Where is it?

**Reply:**

> Hello,
> 
> Thank you for reaching out to us. I understand that you're concerned about the status of your order. To help resolve this, could you please provide me with your order ID? This will allow me to check the tracking information and estimated delivery date for you.
> 
> Best regards,
> Lumora Support

**Judge verdicts:**


<details><summary>Evidence</summary>

- **KB-015**: Lost or stolen packages
If the carrier marks a package as lost, or tracking has not updated for 7 days past the ETA, Lumora offers the customer a choice of a free reshipment or a full refund. If tracking shows 'delivered' but the package is missing, wait 48 hours and check with neighbors before contacting us; we then file a carrier claim.
- **KB-013**: Tracking your order
A tracking number is emailed when your order ships and is shown under Orders. Tracking can take up to 24 hours to show the first scan. The estimated delivery date (ETA) is provided by the carrier.
- **KB-010**: Damaged or defective on arrival
If an item arrives damaged or defective, report it within 30 days of delivery with a photo of the item and packaging. You can choose a free replacement or a full refund; no return fee applies. For final sale items, see KB-007.
- **get_customer**: {"error": "customer_not_found", "email": "new.customer@example.net"}

</details>

## EV-66: تأخير

**Customer:** عذاب معكم، الطلب ORD-10006 متأخر أكثر من أسبوع والتتبع ما تحرك.

**Reply:**

> مرحباً إيثان،
> 
> نعتذر عن التأخير في وصول طلبك رقم ORD-10006. وفقًا للتتبع، يُظهر أن الشحنة في مرحلة النقل حاليًا. وفقًا لسياسة Lumora، لا يمكن إلغاء الطلب بعد الشحن، ولكن يمكنك إرجاع المنتج خلال 30 يومًا من تاريخ الاستلام إذا رغبت.
> 
> لقد تم تطبيق سياسة التتبع المذكورة في KB-014، حيث يمكن فتح طلب تتبع مع شركة النقل NorthPost لمساعدتنا في تتبع الطلب. سنقوم بذلك قريباً.
> 
> إذا كنت ترغب في معرفة المزيد عن إجراءات الإرجاع أو إذا كنت بحاجة إلى مساعدة إضافية، فلا تتردد في الرد.
> 
> فريق دعم Lumora

**Judge verdicts:**


<details><summary>Evidence</summary>

- **KB-014**: تأخر الشحنات
التأخير من 1 إلى 4 أيام عمل بعد التاريخ المتوقع شائع ويُحل عادة دون أي إجراء. إذا تأخر الطلب 5 أيام عمل أو أكثر عن التاريخ المتوقع، يفتح فريق الدعم طلب تتبع (trace) مع شركة الشحن، ويستغرق ذلك حتى 3 أيام عمل.
- **KB-013**: تتبع الطلب
يُرسل رقم التتبع بالبريد الإلكتروني عند شحن الطلب ويظهر في قسم Orders. قد يستغرق ظهور أول تحديث للتتبع حتى 24 ساعة. تاريخ التسليم المتوقع (ETA) تحدده شركة الشحن.
- **KB-009**: إلغاء الطلب
يمكن إلغاء الطلب مع استرداد كامل المبلغ طالما أن حالته 'processing'. بعد شحن الطلب لا يمكن إلغاؤه؛ بدلاً من ذلك يمكن إرجاعه بعد التسليم وفق KB-006. يتم إصدار مبلغ الإلغاء فوراً ويظهر خلال 3-5 أيام عمل.
- **get_customer**: {"customer_id": "CUST-008", "name": "Ethan Brooks", "plan": "pro", "tenure_months": 9, "is_vip": false, "plan_renewed_at": "2026-02-14", "order_ids": ["ORD-10006", "ORD-10015", "ORD-10141"], "recent_tickets": [{"id": "T-0051", "subject": "Lost my 2FA phone", "category": "account"}, {"id": "T-0080", "subject": "Price dropped after I bought", "category": "other"}]}
- **get_order**: {"id": "ORD-10006", "customer_id": "CUST-008", "status": "in_transit", "items": [{"sku": "CAM-200", "name": "Sentinel Doorbell Camera", "qty": 1, "unit_price": 149.0}], "total": 149.0, "payment": {"method": "card", "status": "paid", "charged_count": 1, "amount": 149.0}, "tracking": {"carrier": "NorthPost", "number": "NO2745844780", "eta": "2026-10-22"}, "created_at": "2026-10-14", "delivered_at": 
- **check_refund_eligibility**: {"order_id": "ORD-10006", "order_total": 149.0, "order_status": "in_transit", "payment_status": "paid", "eligible": false, "type": "none", "refundable_amount": 0.0, "reason": "Order has shipped and cannot be cancelled. It can be returned within 30 days after delivery.", "kb_refs": ["KB-009", "KB-006"]}

</details>

## EV-01: Where is my order?

**Customer:** Hi, can you tell me when order ORD-10009 will arrive? Thanks!

**Reply:**

> Hello Omar,
> 
> Thank you for reaching out. Your order ORD-10009 has been shipped with ParcelGo, and the tracking number is PA0857037245. The estimated delivery date (ETA) is 2026-11-04. Tracking information may take up to 24 hours to show the first scan, but you can monitor the progress using this number.
> 
> If you haven't received any updates within the next few days, please feel free to check the status or contact us again. We are here to assist you.
> 
> Best regards,
> Lumora Support

**Judge verdicts:**


<details><summary>Evidence</summary>

- **KB-013**: Tracking your order
A tracking number is emailed when your order ships and is shown under Orders. Tracking can take up to 24 hours to show the first scan. The estimated delivery date (ETA) is provided by the carrier.
- **KB-009**: Cancelling an order
Orders can be cancelled for a full refund while their status is 'processing'. Once an order has shipped it cannot be cancelled; instead, return it after delivery under KB-006. Cancellation refunds are issued immediately and appear within 3-5 business days.
- **KB-014**: Delayed shipments
Carrier delays of 1-4 business days past the ETA are common and usually resolve without action. If an order is 5 or more business days past its ETA, our support team opens a trace with the carrier, which takes up to 3 business days to complete.
- **get_customer**: {"customer_id": "CUST-002", "name": "Omar Khalil", "plan": "pro", "tenure_months": 18, "is_vip": false, "plan_renewed_at": "2026-10-28", "order_ids": ["ORD-10001", "ORD-10009", "ORD-10043", "ORD-10064"], "recent_tickets": [{"id": "T-0057", "subject": "Package lost", "category": "shipping"}, {"id": "T-0098", "subject": "Watch not syncing", "category": "technical"}, {"id": "T-0175", "subject": "Item
- **get_order**: {"id": "ORD-10009", "customer_id": "CUST-002", "status": "shipped", "items": [{"sku": "HOM-200", "name": "Halo Smart Bulb 4-Pack", "qty": 1, "unit_price": 44.99}], "total": 44.99, "payment": {"method": "card", "status": "paid", "charged_count": 1, "amount": 44.99}, "tracking": {"carrier": "ParcelGo", "number": "PA0857037245", "eta": "2026-11-04"}, "created_at": "2026-10-29", "delivered_at": null, 

</details>

## EV-09: Change my email

**Customer:** How can I change the email address on my account?

**Reply:**

> Hello Ethan,
> 
> Thank you for reaching out to us. To update your email address, please follow these steps:
> 
> 1. Log in to your Lumora account.
> 2. Go to Account > Profile.
> 3. Update your email address and confirm by clicking the link sent to your new email address.
> 
> If you encounter any issues, feel free to reply to this email, and we'll assist you further.
> 
> Best regards,
> Lumora Support

**Judge verdicts:**


<details><summary>Evidence</summary>

- **KB-027**: Updating your email or profile
Change your name, phone number, or email under Account > Profile. Changing the email sends a confirmation link to the new address and a notice to the old address. Lumora support will never change an account email on request through a ticket.
- **KB-016**: Changing the shipping address
The shipping address can be changed only while the order status is 'processing'. Once an order has shipped, the address cannot be changed by Lumora; you may be able to redirect the package through the carrier's website using the tracking number.
- **KB-025**: Resetting your password
Use 'Forgot password' on the sign-in page. The reset link is valid for 1 hour and can be used once. If the email doesn't arrive within 10 minutes, check spam and make sure you are using the email on your account. Requesting a new link invalidates older links.
- **get_customer**: {"customer_id": "CUST-008", "name": "Ethan Brooks", "plan": "pro", "tenure_months": 9, "is_vip": false, "plan_renewed_at": "2026-02-14", "order_ids": ["ORD-10006", "ORD-10015", "ORD-10141"], "recent_tickets": [{"id": "T-0051", "subject": "Lost my 2FA phone", "category": "account"}, {"id": "T-0080", "subject": "Price dropped after I bought", "category": "other"}]}

</details>
