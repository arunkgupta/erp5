# request is filled by PaymentTransactionGroup_getGroupablePaymentTransactionLineList
from Products.PythonScripts.standard import Object
return Object(total_quantity=container.REQUEST['PaymentTransactionGroup_statGroupablePaymentTransactionLineList.total_quantity']),
