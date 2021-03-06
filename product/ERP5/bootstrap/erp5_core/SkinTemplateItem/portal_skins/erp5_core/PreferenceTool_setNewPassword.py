from AccessControl import getSecurityManager
from Products.ERP5Type.Message import translateString

request = context.REQUEST
new_password = request.get("new_password")
former_password = request.get("current_password")

user = getSecurityManager().getUser()
persons = context.acl_users.erp5_users.getUserByLogin(user)
person = persons[0]

if not person.checkPassword(former_password):
  msg = translateString("Current password is wrong.")
else:
  msg = translateString("Password changed.")
  person.setPassword(new_password)

# clear erp5_content_short cache (see _authenticateCredentials in Products.ERP5Security.ERP5UserManager)
context.portal_caches.clearCache(('erp5_content_short',))
return context.logout()
