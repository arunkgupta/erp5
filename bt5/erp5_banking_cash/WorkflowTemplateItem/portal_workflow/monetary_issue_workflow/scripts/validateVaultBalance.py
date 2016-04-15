from Products.DCWorkflow.DCWorkflow import ValidationFailed
from Products.ERP5Type.Message import Message

transaction = state_change['object']

# use of the constraint
vliste = transaction.checkConsistency()
transaction.log('vliste', vliste)
if len(vliste) != 0:
  raise ValidationFailed, (vliste[0].getMessage(),)

vault = transaction.getSource()
resource = transaction.CashDelivery_checkCounterInventory(source=vault, portal_type='Monetary Issue Line')

# check again that we are in the good accounting date
transaction.Baobab_checkCounterDateOpen(site=vault, date=transaction.getStartDate())

# Get price and total_price.
amount = transaction.getSourceTotalAssetPrice()
total_price = transaction.getTotalPrice(portal_type=['Monetary Issue Line','Cash Delivery Cell'],fast=0)

if resource == 2:
  msg = Message(domain="ui", message="No Resource.")
  raise ValidationFailed, (msg,)
elif amount != total_price:
  msg = Message(domain="ui", message="Amount differ from total price.")
  raise ValidationFailed, (msg,)
elif resource <> 0 :
  msg = Message(domain="ui", message="Insufficient Balance.")
  raise ValidationFailed, (msg,)
