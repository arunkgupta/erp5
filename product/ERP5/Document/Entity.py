##############################################################################
#
# Copyright (c) 2002 Nexedi SARL and Contributors. All Rights Reserved.
#                    Jean-Paul Smets-Solanes <jp@nexedi.com>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from Products.ERP5Type.Utils import assertAttributePortalType
from AccessControl import ClassSecurityInfo
from Products.ERP5Type import Permissions, PropertySheet, Constraint, Interface
from Products.CMFCore.WorkflowCore import WorkflowMethod
from Products.CMFCore.utils import getToolByName

class Entity:
    """
        Mix-in class used by Organisation and Person

        Implements accessors to:

        - default_telephone

        - default_fax

        - default_email

        - default_address
    """

    # Declarative security
    security = ClassSecurityInfo()
    security.declareObjectProtected(Permissions.View)

    security.declareProtected(Permissions.View, 'getDefaultAddressText')
    def getDefaultAddressText(self):
        """
          Returns the default address as a text string
        """
        try:
          return self.getDefaultAddressValue().asText()
        except:
          return ''

    security.declareProtected(Permissions.View, 'getDefaultAddressStreetAddress')
    def getDefaultAddressStreetAddress(self):
        """
          Returns the default address street as a text string
        """
        try:
          return self.getDefaultAddressValue().getStreetAddress()
        except:
          return ''

    security.declareProtected(Permissions.View, 'getDefaultAddressCity')
    def getDefaultAddressCity(self):
        """
          Returns the default address city as a text string
        """
        try:
          return self.getDefaultAddressValue().getCity()
        except:
          return ''

    security.declareProtected(Permissions.View, 'getDefaultCareerTitle')
    def getDefaultCareerTitle(self):
        """
          Returns the default address city as a text string
        """
        try:
          return self.getDefaultCareerValue().getTitle()
        except:
          return ''

    security.declareProtected(Permissions.View, 'getDefaultCareerDescription')
    def getDefaultCareerDescription(self):
        """
	  Returns the default address city as a text string
	"""
	try:
	  return self.getDefaultCareerValue().getDescription()
	except:
	  return ''

    security.declareProtected(Permissions.View, 'getDefaultCareerCollectiveAgreementTitle')
    def getDefaultCareerCollectiveAgreementTitle(self):
        """
          Returns the default address city as a text string
        """
        try:
          return self.getDefaultCareerValue().getCollectiveAgreementTitle()
        except:
          return ''

    security.declareProtected(Permissions.View, 'getDefaultCareerDestinationTitle')
    def getDefaultCareerDestinationTitle(self):
        """
          Returns the default address city as a text string
        """
        try:
          return self.getDefaultCareerValue().getDestinationTitle()
        except:
          return ''

    security.declareProtected(Permissions.View, 'getDefaultCareerStartDate')
    def getDefaultCareerStartDate(self):
        """
          Returns the default address city as a text string
        """
        try:
          return self.getDefaultCareerValue().getStartDate()
        except:
          return None

    security.declareProtected(Permissions.View, 'getDefaultCareerStopDate')
    def getDefaultCareerStopDate(self):
        """
          Returns the default address city as a text string
        """
        try:
          return self.getDefaultCareerValue().getStopDate()
        except:
          return None

    security.declareProtected(Permissions.View, 'getDefaultCareerSalaryLevel')
    def getDefaultCareerSalaryLevel(self):
        """
          Returns the default address city as a text string
        """
        try:
          return self.getDefaultCareerValue().getSalaryLevel()
        except:
          return ''
        
    security.declareProtected(Permissions.View, 'getDefaultCareerSalaryCoefficient')
    def getDefaultCareerSalaryCoefficient(self):
        """
          Returns the default address city as a text string
        """
        try:
          return self.getDefaultCareerValue().getSalaryCoefficient()
        except:
          return ''                                                                               
        
    security.declareProtected(Permissions.View, 'getDefaultAddressRegion')
    def getDefaultAddressRegion(self):
        """
          Returns the default address region as a text string
        """
        try:
         return self.getDefaultAddressValue().getRegion()
        except:
         return ''

    security.declareProtected(Permissions.View, 'getDefaultAddressZipCode')
    def getDefaultAddressZipCode(self):
        """
          Returns the default address zip code as a text string
        """
        try:
          return self.getDefaultAddressValue().getZipCode()
        except:
          return ''

    security.declareProtected(Permissions.View, 'getDefaultTelephoneText')
    def getDefaultTelephoneText(self):
        """
          Returns the default telephone as a text string
        """
        try:
          return self.getDefaultTelephone().asText()
        except:
          return ''

    security.declareProtected(Permissions.View, 'getDefaultTelephoneNumber')
    def getDefaultTelephoneNumber(self):
        """
          Returns the default telephone number
        """
        try:
          return self.getDefaultTelephone().getTelephoneNumber()
        except:
          return ''								      

    security.declareProtected(Permissions.View, 'getDefaultFaxText')
    def getDefaultFaxText(self):
        """
          Returns the default fax as a text string
        """
        try:
          return self.getDefaultFax().asText()
        except:
          return ''

    security.declareProtected(Permissions.View, 'getDefaultFaxNumber')
    def getDefaultFaxNumber(self):
        """
          Returns the default fax number
        """
        try:
          return self.getDefaultFax().getTelephoneNumber()
        except:
          return ''

    security.declareProtected(Permissions.View, 'getDefaultEmailText')
    def getDefaultEmailText(self):
        """
          Returns the default email as a text string
        """
        try:
          return self.getDefaultEmail().asText()
        except:
          return ''

    security.declareProtected(Permissions.ModifyPortalContent, 'setDefaultAddress')
    def setDefaultAddress(self, coordinate):
        """
          Updates the default address from a standard text string
        """
        self._setDefaultAddress(coordinate)
        self.reindexObject()

    security.declareProtected(Permissions.ModifyPortalContent, 'setDefaultCareerTitle')
    def setDefaultCareerTitle(self, coordinate):
        """
          Updates the default address from a standard text string
        """
        self._setDefaultCareerTitle(coordinate)
        self.reindexObject()

    security.declareProtected(Permissions.ModifyPortalContent, 'setDefaultCareerDescription')
    def setDefaultCareerDescription(self, coordinate):
        """
	  Updates the default address from a standard text string
	"""
	self._setDefaultCareerDescription(coordinate)
	self.reindexObject()

    security.declareProtected(Permissions.ModifyPortalContent, 'setDefaultCareerCollectiveAgreementTitle')
    def setDefaultCareerCollectiveAgreementTitle(self, coordinate):
        """
          Updates the default address from a standard text string
        """
        self._setDefaultCareerCollectiveAgreementTitle(coordinate)
        self.reindexObject()                                                 

    security.declareProtected(Permissions.ModifyPortalContent, 'setDefaultCareerStartDate')
    def setDefaultCareerStartDate(self, coordinate):
        """
          Updates the default address from a standard text string
        """
        self._setDefaultCareerStartDate(coordinate)
        self.reindexObject()

    security.declareProtected(Permissions.ModifyPortalContent, 'setDefaultCareerStopDate')
    def setDefaultCareerStopDate(self, coordinate):
        """
          Updates the default address from a standard text string
        """
        self._setDefaultCareerStopDate(coordinate)
        self.reindexObject()

    security.declareProtected(Permissions.ModifyPortalContent, 'setDefaultCareerSalaryLevel')
    def setDefaultCareerSalaryLevel(self, coordinate):
        """
          Updates the default address from a standard text string
        """
        self._setDefaultCareerSalaryLevel(coordinate)
        self.reindexObject()

    security.declareProtected(Permissions.ModifyPortalContent, 'setDefaultCareerSalaryCoefficient')
    def setDefaultCareerSalaryCoefficient(self, coordinate):
        """
          Updates the default address from a standard text string
        """
        self._setDefaultCareerSalaryCoefficient(coordinate)
        self.reindexObject()                                                    

    security.declareProtected(Permissions.ModifyPortalContent, 'setDefaultAddressText')
    def setDefaultAddressText(self, coordinate):
        """
          Updates the default address from a standard text string
        """
        self._setDefaultAddressText(coordinate)
        self.reindexObject()

    security.declareProtected(Permissions.ModifyPortalContent, 'setDefaultAddressRegion')
    def setDefaultAddressRegion(self, coordinate):
        """
          Updates the default address from a standard text string
        """
        self._setDefaultAddressRegion(coordinate)
        self.reindexObject()

    security.declareProtected(Permissions.ModifyPortalContent, 'setDefaultAddressCity')
    def setDefaultAddressCity(self, coordinate):
        """
          Updates the default address from a standard text string
        """
        self._setDefaultAddressCity(coordinate)
        self.reindexObject()

    security.declareProtected(Permissions.ModifyPortalContent, 'setDefaultAddressZipCode')
    def setDefaultAddressZipCode(self, coordinate):
        """
          Updates the default address from a standard text string
        """
        self._setDefaultAddressZipCode(coordinate)
        self.reindexObject()

    security.declareProtected(Permissions.ModifyPortalContent, 'setDefaultAddressStreetAddress')
    def setDefaultAddressStreetAddress(self, coordinate):
        """
          Updates the default address from a standard text string
        """
        self._setDefaultAddressStreetAddress(coordinate)
        self.reindexObject()

    security.declareProtected(Permissions.ModifyPortalContent, 'setDefaultTelephoneText')
    def setDefaultTelephoneText(self, coordinate):
        """
          Updates the default telephone from a standard text string
        """
        self._setDefaultTelephoneText(coordinate)
        self.reindexObject()

    security.declareProtected(Permissions.ModifyPortalContent, 'setDefaultTelephoneNumber')
    def setDefaultTelephoneNumber(self, coordinate):
        """
          Updates the default telephone number
        """
        self._setDefaultTelephoneNumber(coordinate)
        self.reindexObject()							  

    security.declareProtected(Permissions.ModifyPortalContent, 'setDefaultFaxText')
    def setDefaultFaxText(self, coordinate):
        """
          Updates the default fax from a standard text string
        """
        self._setDefaultFaxText(coordinate)
        self.reindexObject()

    security.declareProtected(Permissions.ModifyPortalContent, 'setDefaultFaxNumber')
    def setDefaultFaxNumber(self, coordinate):
        """
	  Updates the default fax number
	"""
	self._setDefaultFaxNumber(coordinate)
	self.reindexObject()
							  
    security.declareProtected(Permissions.ModifyPortalContent, 'setDefaultEmailText')
    def setDefaultEmailText(self, coordinate):
        """
          Updates the default email from a standard text string
        """
        self._setDefaultEmailText(coordinate)
        self.reindexObject()

    ### Private methods - no reindexing
    security.declarePrivate('_setDefaultAddress')
    def _setDefaultAddress(self, coordinate):
        assertAttributePortalType(self, 'default_address', 'Address')
        if not hasattr(self,'default_address'):
          self.invokeFactory( type_name='Address'
                            , id='default_address'
                            )
        self.default_address = coordinate

    security.declarePrivate('_setDefaultAddressText')
    def _setDefaultAddressText(self, coordinate):
        assertAttributePortalType(self, 'default_address', 'Address')
        if not hasattr(self,'default_address'):
          self.invokeFactory( type_name='Address'
                            , id='default_address'
                            )
        self.default_address.fromText(coordinate)

    security.declarePrivate('_setDefaultAddressCity')
    def _setDefaultAddressCity(self, value):
        assertAttributePortalType(self, 'default_address', 'Address')
        if not hasattr(self,'default_address'):
          self.invokeFactory( type_name='Address'
                            , id='default_address'
                            )
        self.default_address.setCity(value)

    security.declarePrivate('_setDefaultAddressZipCode')
    def _setDefaultAddressZipCode(self, value):
        assertAttributePortalType(self, 'default_address', 'Address')
        if not hasattr(self,'default_address'):
          self.invokeFactory( type_name='Address'
                            , id='default_address'
                            )
        self.default_address.setZipCode(value)

    security.declarePrivate('_setDefaultAddressStreetAddress')
    def _setDefaultAddressStreetAddress(self, value):
        assertAttributePortalType(self, 'default_address', 'Address')
        if not hasattr(self,'default_address'):
          self.invokeFactory( type_name='Address'
                            , id='default_address'
                            )
        self.default_address.setStreetAddress(value)

    security.declarePrivate('_setDefaultAddressRegion')
    def _setDefaultAddressRegion(self, value):
        assertAttributePortalType(self, 'default_address', 'Address')
        if not hasattr(self,'default_address'):
          self.invokeFactory( type_name='Address'
                            , id='default_address'
                            )
        self.default_address.setRegion(value)

    security.declarePrivate('_setDefaultCareerTitle')
    def _setDefaultCareerTitle(self, coordinate):
        assertAttributePortalType(self, 'default_career', 'Career')
        if not hasattr(self,'default_career'):
          self.invokeFactory( type_name='Career'
                            , id='default_career'
                            )
        self.default_career.setTitle(coordinate)

    security.declarePrivate('_setDefaultCareerDescription')
    def _setDefaultCareerDescription(self, coordinate):
	assertAttributePortalType(self, 'default_career', 'Career')
	if not hasattr(self,'default_career'):
	  self.invokeFactory( type_name='Career'
	                    , id='default_career'
	                    )
	self.default_career.setDescription(coordinate)

    security.declarePrivate('_setDefaultCareerCollectiveAgreementTitle')
    def _setDefaultCareerCollectiveAgreementTitle(self, coordinate):
        assertAttributePortalType(self, 'default_career', 'Career')
        if not hasattr(self,'default_career'):
          self.invokeFactory( type_name='Career'
                            , id='default_career'
                            )
        self.default_career.setCollectiveAgreementTitle(coordinate)
							  
    security.declarePrivate('_setDefaultCareerStartDate')
    def _setDefaultCareerStartDate(self, coordinate):
        assertAttributePortalType(self, 'default_career', 'Career')
        if not hasattr(self,'default_career'):
          self.invokeFactory( type_name='Career'
                            , id='default_career'
                            )
        self.default_career.setStartDate(coordinate)

    security.declarePrivate('_setDefaultCareerStopDate')
    def _setDefaultCareerStopDate(self, coordinate):
        assertAttributePortalType(self, 'default_career', 'Career')
        if not hasattr(self,'default_career'):
          self.invokeFactory( type_name='Career'
                            , id='default_career'
                            )
        self.default_career.setStopDate(coordinate)

    security.declarePrivate('_setDefaultCareerSalaryLevel')
    def _setDefaultCareerSalaryLevel(self, coordinate):
        assertAttributePortalType(self, 'default_career', 'Career')
        if not hasattr(self,'default_career'):
          self.invokeFactory( type_name='Career'
                            , id='default_career'
                            )
        self.default_career.setSalaryLevel(coordinate)
                                              
    security.declarePrivate('_setDefaultCareerSalaryCoefficient')
    def _setDefaultCareerSalaryCoefficient(self, coordinate):
        assertAttributePortalType(self, 'default_career', 'Career')
        if not hasattr(self,'default_career'):
          self.invokeFactory( type_name='Career'
                            , id='default_career'
                            )
        self.default_career.setSalaryCoefficient(coordinate)
                                            
    security.declarePrivate('_setDefaultTelephoneText')
    def _setDefaultTelephoneText(self, coordinate):
        assertAttributePortalType(self, 'default_telephone', 'Telephone')
        if not hasattr(self,'default_telephone'):
          self.invokeFactory( type_name='Telephone'
                            , id='default_telephone'
                            )
        self.default_telephone.fromText(coordinate)

    security.declarePrivate('_setDefaultTelephoneNumber')
    def _setDefaultTelephoneNumber(self, coordinate):
        assertAttributePortalType(self, 'default_telephone', 'Telephone')
        if not hasattr(self,'default_telephone'):
          self.invokeFactory( type_name='Telephone'
                            , id='default_telephone'
                            )
        self.default_telephone.setTelephoneNumber(coordinate)

    security.declarePrivate('_setDefaultFaxText')
    def _setDefaultFaxText(self, coordinate):
        assertAttributePortalType(self, 'default_fax', 'Fax')
        if not hasattr(self,'default_fax'):
          self.invokeFactory( type_name='Fax'
                            , id='default_fax'
                            )
        self.default_fax.fromText(coordinate)

    security.declarePrivate('_setDefaultFaxNumber')
    def _setDefaultFaxNumber(self, coordinate):
        assertAttributePortalType(self, 'default_fax', 'Fax')
	if not hasattr(self,'default_fax'):
	  self.invokeFactory( type_name='Fax'
			    , id='default_fax'
			    )
	self.default_fax.setTelephoneNumber(coordinate)
							  
    security.declarePrivate('_setDefaultEmailText')
    def _setDefaultEmailText(self, coordinate):
        assertAttributePortalType(self, 'default_email', 'Email')
        if not hasattr(self,'default_email'):
          self.invokeFactory( type_name='Email'
                            , id='default_email'
                            )
        self.default_email.fromText(coordinate)

    security.declareProtected(Permissions.ModifyPortalContent, 'validate')
    def validate(self):
      """
        Sets the entity to validated
      """
      pass

    validate = WorkflowMethod(validate)

    security.declareProtected(Permissions.ModifyPortalContent, 'invalidate')
    def invalidate(self):
      """
        Sets the entity to invalidated
      """
      pass

    invalidate = WorkflowMethod(invalidate)

    security.declareProtected(Permissions.AccessContentsInformation, 'getValidationState')
    def getValidationState(self, id_only=1):
      """
        Returns the current state in validation
      """
      portal_workflow = getToolByName(self, 'portal_workflow')
      wf = portal_workflow.getWorkflowById('validation_workflow')
      return wf._getWorkflowStateOf(self, id_only=id_only )
