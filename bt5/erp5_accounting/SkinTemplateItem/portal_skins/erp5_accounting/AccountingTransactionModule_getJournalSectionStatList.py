from Products.PythonScripts.standard import Object
request = container.REQUEST
portal = context.getPortalObject()

return [ Object(
           debit=request.get(
      'AccountingTransactionModule_getJournalSectionLineList.total_debit'),
           credit=request.get(
      'AccountingTransactionModule_getJournalSectionLineList.total_credit')) ]
