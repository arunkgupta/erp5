total = 0
for line in context.objectValues(
        portal_type = context.getPortalAccountingMovementTypeList()) :
  total += line.getDestinationInventoriatedTotalAssetCredit()
  
return total
