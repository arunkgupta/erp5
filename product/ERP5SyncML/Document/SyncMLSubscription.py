# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2002 Nexedi SARL and Contributors. All Rights Reserved.
#          Sebastien Robin <seb@nexedi.com>
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
##############################################################################

from base64 import b16encode, b16decode
from logging import getLogger
from urlparse import urlparse
from lxml import etree
from copy import deepcopy

from AccessControl import ClassSecurityInfo
from AccessControl.SecurityManagement import newSecurityManager
from DateTime import DateTime

from Products.ERP5Type.XMLObject import XMLObject
from Products.ERP5Type import Permissions, PropertySheet
from Products.ERP5Type.Utils import deprecated
from Products.ERP5SyncML.XMLSyncUtils import getConduitByName, \
     buildAnchorFromDate
from Products.ERP5SyncML.SyncMLConstant import MAX_OBJECTS, ACTIVITY_PRIORITY,\
     NULL_ANCHOR
from Products.ERP5SyncML.SyncMLMessage import SyncMLResponse
from Products.ERP5SyncML.Transport.HTTP import HTTPTransport
from Products.ERP5SyncML.Transport.File import FileTransport
from Products.ERP5SyncML.Transport.Mail import MailTransport
from Products.ERP5SyncML.Transport.ERP5 import ERP5Transport
from Products.ERP5SyncML.SyncMLConstant import MAX_LEN, ADD_ACTION, \
    REPLACE_ACTION
from Products.ERP5SyncML.XMLSyncUtils import cutXML

transport_scheme_dict = {
  "http" : HTTPTransport(),
  "https" : HTTPTransport(),
  "file" : FileTransport(),
  "mail" : MailTransport(),
  "erp5" : ERP5Transport(),
  }

syncml_logger = getLogger('ERP5SyncML')

MAX_OBJECT_PER_MESSAGE = 300

RETRO_COMPATIBLE = True

_MARKER = []
class SyncMLSubscription(XMLObject):
  """
  """

  security = ClassSecurityInfo()
  security.declareObjectProtected(Permissions.AccessContentsInformation)

  # Declarative properties
  property_sheets = ( PropertySheet.Base
                    , PropertySheet.XMLObject
                    , PropertySheet.CategoryCore
                    , PropertySheet.DublinCore
                    , PropertySheet.Reference
                    , PropertySheet.Login
                    , PropertySheet.Url
                    , PropertySheet.Gpg
                    , PropertySheet.Data
                    , PropertySheet.SyncMLSubscription
                    , PropertySheet.SyncMLSubscriptionConstraint )

  security.declarePrivate('finishSynchronization')
  def finishSynchronization(self,):
    """
    Last method call that will make sure to finish the sync process
    and reset all necessary variable
    """
    self.finish()  # Worflow transition
    syncml_logger.info('--- synchronization ended on the server side ---')
    if self.getAuthenticationState() == 'logged_in':
      self.logout()
    self._edit(authenticated_user=None)

  security.declarePrivate('getAndIndex')
  def getAndIndex(self, callback, method_kw, activate_kw, **kw):
    """
    This methods is called by the asynchronous engine to index source
    data in sql table

    callback : method to call in activity
    method_kw : callback's parameters
    activate_kw : activity parameters to pass to activate call
    kw : any parameter getAndActivate can required if it calls itself
    """
    search_kw = dict(kw)
    packet_size = search_kw.pop('packet_size', 30)
    limit = packet_size * search_kw.pop('activity_count', 100)
    try:
      r = self.getDocumentIdList(limit=limit, **search_kw)  # It is assumed that
                                                            # the result is sorted
    except TypeError:
      if not RETRO_COMPATIBLE:
        raise
      else:
        syncml_logger.warning("Script %s does not accept paramaters limit=%s kw=%s" %
                              (self.getListMethodId(), limit, search_kw,))
        r = self.getDocumentList()  # It is assumed that
                                    # the result is sorted
    result_count = len(r)
    generated_other_activity = False
    if result_count:
      syncml_logger.info("getAndIndex : got %d, %r result, limit = %d, packet %d" %
                         (result_count, r, limit, packet_size))
      if result_count == limit:
        # Recursive call to prevent too many activity generation
        next_kw = dict(activate_kw, priority=1+activate_kw.get('priority', 1))
        kw["min_id"] = r[-1].getId()
        syncml_logger.info("--> calling getAndActivate in activity, min = %s" %
                           (kw["min_id"],))

        self.activate(**next_kw).getAndActivate(
          callback, method_kw, activate_kw, **kw)
        generated_other_activity = True

      r = [x.getPath() for x in r]
      activate = self.getPortalObject().portal_synchronizations.activate
      callback_method = getattr(activate(**activate_kw), callback)
      if generated_other_activity:
        for i in xrange(0, result_count, packet_size):
          syncml_logger.info("-- getAndIndex : recursive call, generating for %s"
                             % (r[i:i+packet_size],))
          callback_method(path_list=r[i:i+packet_size],
                          activate_kw=activate_kw,
                          **method_kw)
      else:
        if result_count > packet_size:
          for i in xrange(0, result_count-packet_size, packet_size):
            syncml_logger.info("-- getAndIndex : i %s, call, generating for %s : %s" %
                               (i, r[i:i+packet_size], activate_kw))
            callback_method(path_list=r[i:i+packet_size],
                            **method_kw)
          final_min = i +  packet_size
        else:
          final_min = 0
        syncml_logger.info("---- getAndIndex : final call for %s %s : %s" \
                           %(final_min, r[final_min:], activate_kw))
        callback_method(path_list=r[final_min:],
                        activate_kw=activate_kw,
                        **method_kw)
    return result_count

  security.declarePrivate('getSearchableSourcePath')
  def getSearchableSourcePath(self):
    """
    Return the path of the subscription that will be used in sql table
    _ char must be escaped because of the LIKE behaviour
    """
    return "%s%%" % (self.getSourceValue().getPath().replace("_","\_"),)

  def sendSyncCommand(self, min_gid, max_gid, message_id, activate_kw):
    """
    This methods is intented to be called by asynchronous engine in activity to
    send sync commands for a subset of data
    """
    # Build Message
    syncml_response = SyncMLResponse()
    # XXX Make a generic method that already exists in engines
    syncml_response.addHeader(
      session_id=self.getSessionId(),
      message_id=message_id,
      target=self.getUrlString(),
      source=self.getSubscriptionUrlString())
    syncml_response.addBody()

    self._getSyncMLData(
      syncml_response=syncml_response,
      min_gid=min_gid,
      max_gid=max_gid,
      )

    # Send the message in activity to prevent recomputation of data in case of
    # transport failure
    # activate_kw["group_method_id"] = None
    # activate_kw["group_method_cost"] = .05
    self.activate(**activate_kw).sendMessage(xml=str(syncml_response))


  security.declarePrivate('getAndActivate')
  def getAndActivate(self, callback, activate_kw, **kw):
    """
    This methods is called by the asynchronous engine to split activity
    generation into activities.

    callback : method to call in activity
    activate_kw : activity parameters to pass to activate call
    kw : any parameter getAndActivate can required if it calls itself

    Last activate must wait for all other activities to be processed in order
    to set the Final tag in the message, this is required by SyncML DS
    specification
    """
    # The following implementation is base on CatalogTool.searchAndActivate
    # It might be possible to move a part of this code into the domain class
    # so that it can be configurable as not all backend are optimised for
    # this default implementation
    search_kw = dict(kw)
    packet_size = search_kw.pop('packet_size', 30)
    limit = packet_size * search_kw.pop('activity_count', 100)

    # We must know if we have a lower limit or not to propagate
    if not kw.has_key("strict_min_gid"):
      first_call = True
    else:
      first_call = False

    search_kw.update({"stict_min_gid" : None,
                      "min_gid" : None,
                      "max_gid" : None,
                      "limit" : limit,
                      "path" : self.getSearchableSourcePath()})

    r = [x.gid for x in self.z_get_syncml_gid_list(**search_kw)]
    result_count = len(r)
    generated_other_activity = False
    if result_count:
      syncml_logger.info("getAndActivate : got %d result" % (result_count,))
      if result_count == limit:
        # Recursive call to prevent too many activity generation
        next_kw = dict(activate_kw, priority=1+activate_kw.get('priority', 1))
        kw["strict_min_gid"] = r[-1]
        syncml_logger.info("--> calling getAndActivate in activity, min = %s" %
                           (kw["min_gid"],))
        self.activate(**next_kw).getAndActivate(
          callback, activate_kw, **kw)
        generated_other_activity = True

      message_id_list = self.getNextMessageIdList(id_count=result_count)
      # XXX maybe (result_count / packet_size) + 1 instead of result_count
      message_id_list.reverse()  # We pop each id in the following loop
      activate = self.activate
      callback_method = getattr(activate(**activate_kw), callback)
      if generated_other_activity:
        #  XXX Can be factorized with following code
        # upper_limit of xrange + some check ???
        for i in xrange(0, result_count, packet_size):
          syncml_logger.info("-- getAndActivate : recursive call")
          if first_call:
            min_gid = None
            first_call = False
          else:
            min_gid = r[i]
          callback_method(min_gid=min_gid,
                          max_gid=r[i+packet_size],
                          message_id=message_id_list.pop(),
                          activate_kw=activate_kw)
      else:
        i = 0
        if result_count > packet_size:
          for i in xrange(0, result_count-packet_size, packet_size):
            syncml_logger.info("-- getAndActivate call")
            if first_call:
              min_gid = None
              first_call = False
            else:
              min_gid = r[i]
            callback_method(min_gid=min_gid,
                            max_gid=r[i+packet_size],
                            message_id=message_id_list.pop(),
                            activate_kw=activate_kw)
          final_min = i +  packet_size
        else:
          final_min = 0
        # Final activity must be tell there is no upper limit
        # XXX maybe re-put here the final tag of message to avoid empty message
        syncml_logger.info("---- getAndActivate : final call")
        if first_call:
          min_gid = None
        else:
          min_gid = r[final_min]
        callback_method(min_gid=min_gid,
                        max_gid=None, # No limit when last call
                        message_id=message_id_list.pop(),
                        activate_kw=activate_kw)
    return result_count

  security.declarePrivate('sendMessage')
  def sendMessage(self, xml):
    """
    Send the syncml response according to the protocol defined for the target
    """
    # First register sent message in case we received same message multiple time
    # XXX-must be check according to specification
    # XXX-performance killer in scalable environment
    # XXX maybe use memcached instead for this ?
    # self.setLastSentMessage(xml)

    # XXX must review all of this
    # - source/target must be relative URI (ie
    # portal_synchronizations/person_pub) so that there is no need to defined
    # source_reference
    # -content type must be get from SyncMLMessage directly

    # SyncML can transmit xml or wbxml, transform the xml when required
    # XXX- This must be manager in syncml message representation
    to_url = self.getUrlString()
    scheme = urlparse(to_url)[0]

    if self.getIsSynchronizedWithErp5Portal() and scheme in ("http", "https"):
      # XXX will be removed soon
      to_url = self.getUrlString() + '/portal_synchronizations/readResponse'

    # call the transport to send data
    transport_scheme_dict[scheme].send(to_url=to_url, data=xml,
                                       sync_id=self.getDestinationReference(),
                                       content_type=self.getContentType())

  def _loginUser(self, user_id=None):
    """
    Log in with the user provided or defined on self
    """
    if not user_id:
      user_id = self.getProperty('authenticated_user')
    if user_id:
      # TODO: make it work for users existing anywhere
      user_folder = self.getPortalObject().acl_users
      try:
        user = user_folder.getUserById(user_id).__of__(user_folder) # __of__ might got AttributeError
      except AttributeError:
        raise ValueError("User %s cannot be found in user folder, \
              synchronization cannot work with this kind of user" % (user_id,))
      if user is None:
        raise ValueError("User %s cannot be found in user folder, \
              synchronization cannot work with this kind of user" % (user_id,))
      else:
        newSecurityManager(None, user)
    else:
      raise ValueError(
        "Impossible to find a user to log in, subscription = %s"
        % (self.getRelativeUrl()))


  security.declarePrivate('applyActionList')
  def applyActionList(self, syncml_request, syncml_response, simulate=False):
    """
    Browse the list of sync command received, apply them and generate answer
    """
    for action in syncml_request.sync_command_list:
      self.applySyncCommand(
        action=action,
        request_message_id=syncml_request.header["message_id"],
        syncml_response=syncml_response,
        simulate=simulate)

  security.declarePrivate('applySyncCommand')
  def applySyncCommand(self, action, request_message_id, syncml_response,
                       simulate=False):
    """
    Apply a sync command received
    Here is the main algorithm :
    - try to get the signature for the GID ( some mode does not required it)
    - apply the action
    - update signature
    - generate the status command
    """
    conduit = self.getConduit()
    destination = self.getSourceValue()
    conflict_list = []
    status_code = 'success'
    # First retrieve the GID of the object we want to modify
    gid = action["source"] or action["target"]
    # Retrieve the signature for the current GID
    path_list = []
    signature = self.getSignatureFromGid(gid)
    if syncml_response is not None:  # No response to send when no signature to create
      document = self.getDocumentFromGid(gid)
      if signature is None:
        # Create a new signature when needed
        # XXX what if it does not happen on a Add command ?
        signature = self.newContent(
          portal_type='SyncML Signature',
          id=gid,
          )
        syncml_logger.info("Created a signature for %s - document : %s"
                            % (signature.getPath(), document))
        if document is not None:
          signature.setReference(document.getPath())

      elif signature.getValidationState() == 'synchronized':
        # Reset status of signature synchronization
        signature.drift()
      path_list.append(signature.getPath())
      force = signature.isForce()  # XXX-must check the use of this later
    else:
      force = True  # Always erease data in this mode
      document = None  # For now, do no try to retrieve previous version of document
      # XXX this has to be managed with a property
      # XXX Some improvement can also be done to retrieve a list of document at once

    # Get the data
    if 'xml_data' in action:
      # Rebuild an Element
      incoming_data = etree.fromstring(action["xml_data"])
    else:  # Raw data
      incoming_data = action['raw_data']
    # XXX must find a way to check for No data received here
    if not action['more_data']:
      # This is the last chunk of a partial xml
      # or this is just an entire data chunk
      if signature and signature.hasPartialData():
        # Build data with already stored data
        signature.appendPartialData(incoming_data)
        incoming_data = signature.getPartialData()
        signature.setPartialData(None)

      # Browse possible actions
      if action["command"] == 'Add':
        status_code = "item_added"  # Default status code for addition
        if document is None:
          # This is the default behaviour when getting an "Add" command
          # we create new document from the received data
          syncml_logger.info("Calling addNode with no previous document found")
          add_data = conduit.addNode(xml=incoming_data,
                                     object=destination,
                                     signature=signature,
                                     domain=self)
          conflict_list.extend(add_data['conflict_list'])
          # Retrieve directly the document from addNode
          document = add_data['object']
          if document is None:
            raise ValueError("Adding a document failed, data = %s"
                             % (etree.tostring(incoming_data,
                                               pretty_print=True),))
        else:
          # Document was retrieved from the database
          actual_xml = conduit.getXMLFromObjectWithGid(document, gid,
                         xml_mapping=\
                         self.getXmlBindingGeneratorMethodId(force=True),
                         context_document=self.getPath())
          # use gid to compare because their ids can be different
          incoming_data = conduit.replaceIdFromXML(incoming_data, 'gid', gid)
          # produce xupdate
          data_diff = conduit.generateDiff(new_data=incoming_data,
                                           former_data=actual_xml)

          if data_diff and len(data_diff):
            # XXX Here maybe a conflict must be raised as document was never
            # synchronized and we try to add one which is different
            syncml_logger.critical("trying to add data, but already existing object exists, diff is\n%s" % (data_diff))

          conflict_list.extend(conduit.updateNode(
                                      xml=data_diff,
                                      object=document,
                                      previous_xml=actual_xml,
                                      force=force,
                                      simulate=simulate,
                                      reset=True,
                                      signature=signature,
                                      domain=self))

        xml_document = incoming_data
        if not isinstance(xml_document, basestring):
          # XXX using deepcopy to remove parent link - must be done elsewhere
          xml_document = deepcopy(xml_document)
          # Remove useless namespace
          etree.cleanup_namespaces(xml_document)
          xml_document = etree.tostring(xml_document, encoding='utf-8',
                                        pretty_print=True)

        if isinstance(xml_document, unicode):
          xml_document = xml_document.encode('utf-8')
        # Link the signature to the document
        if signature:
          signature.setReference(document.getPath())
      elif action["command"] == 'Replace':
        status_code = "success"  # Default status code for addition
        if document is not None:
          signature = self.getSignatureFromGid(gid)
          previous_xml = signature.getData()
          if previous_xml:
            # Make xml consistent XXX should be part of the conduit work
            # XXX this should not happen if we call replaceIdFromXML when
            # editing signature
            previous_xml = conduit.replaceIdFromXML(previous_xml, 'gid', gid)
          conflict_list += conduit.updateNode(xml=incoming_data,
                                              object=document,
                                              previous_xml=previous_xml,
                                              force=force,
                                              signature=signature,
                                              simulate=False, #simulate,
                                              domain=self)
          if previous_xml:
            # here compute patched data with given diff
            xml_document = conduit.applyDiff(previous_xml, incoming_data)
            xml_document = conduit.replaceIdFromXML(xml_document, 'id',
                                                    document.getId(),
                                                    as_string=True)
          else:
            raise ValueError("Got a signature with no data for %s" % (gid,))
        else:
          # Try to apply an update on a delete document
          # What to do ?
          raise ValueError("No document found to apply update")

      elif action['command'] == 'Delete':
        status_code="success"
        document = self.getDocumentFromGid(signature.getId())
        # syncml_logger.info("Deleting signature %s & doc %s" %(signature.getPath(),
        #                                                       document.getPath()))
        path_list.remove(signature.getPath())
        if document is not None:
          # XXX Can't we get conflict ?
          # XXX Review the code to prevent retrieving document
          conduit.deleteNode(xml=incoming_data,
                             object=destination,
                             object_id=document.getId())
          # Delete signature
          self._delObject(gid)
        else:
          syncml_logger.error("Document with gid %s is already deleted"
                             % (gid,))

        self.z_delete_data_from_path(path="%s" %(signature.getPath(),))
      else:
        raise ValueError("Unknown command %s" %(action['command'],))

      # Now update signature status regarding conflict list
      if action['command'] != "Delete" and signature:
        if len(conflict_list):
          status_code="conflict"
          signature.changeToConflict()
          # Register the data received which generated the diff
          # XXX Why ?
          if not isinstance(incoming_data, basestring):
            incoming_data = etree.tostring(incoming_data,
                                           encoding='utf-8')
          signature.setPartialData(incoming_data)
        else:
          signature.setData(str(xml_document))
          signature.synchronize()
        syncml_logger.debug("change state of signature to %s"
                           % (signature.getValidationState(),))

      if signature:
        # Generate status about the object synchronized
        # No need to generate confirmation when no signature are stored
        syncml_response.addConfirmationMessage(
          command=action['command'],
          sync_code=status_code,
          target_ref=action["target"],
          source_ref=action["source"],
          command_ref=action["command_id"],
          message_ref=request_message_id)

    else:  # We want to retrieve more data
      syncml_logger.info("we need to retrieve more data for %s" % (signature,))
      if signature.getValidationState() != 'partial':
        signature.changeToPartial()
      signature.appendPartialData(incoming_data)
      # XXX Must check if size is present into the xml
      # if not, client might ask it to server with a 411 alert
      # in this case, do not process received data
      syncml_response.addConfirmationMessage(
        command=action['command'],
        sync_code='chunk_accepted',
        target_ref=action["target"],
        source_ref=action["source"],
        command_ref=action["command_id"],
        message_ref=request_message_id)
      # Must add an alert message to ask remaining data to be processed
      # Alert 222 must be generated
      # XXX Will be into the Sync tag -> bad
      syncml_response.addAlertCommand(
            alert_code='next_message',
            target=self.getDestinationReference(),
            source=self.getSourceReference(),
            last_anchor=self.getLastAnchor(),
            next_anchor=self.getNextAnchor())
    # Index signature with their new value
    self.SQLCatalog_indexSyncMLDocumentList(path_list)

  def _sendFinalMessage(self):
    """
    Send an empty message containing the final tag to notify the end of
    the "sending_modification" stage of the synchronization
    """
    syncml_response = SyncMLResponse()
    syncml_response.addHeader(
      session_id=self.getSessionId(),
      message_id=self.getNextMessageId(),
      target=self.getUrlString(),
      source=self.getSubscriptionUrlString())
    syncml_response.addBody()
    syncml_response.addFinal()

    final_activate_kw = {
      'after_method_id' : ("processServerSynchronization",
                           "processClientSynchronization"),
      'priority' :ACTIVITY_PRIORITY + 1,
      'tag' : "%s_delete" %(self.getRelativeUrl(),)
      }
    syncml_logger.info("Sending final message for modificationson on %s"
                            % (self.getRelativeUrl(),))
    self.activate(**final_activate_kw).sendMessage(xml=str(syncml_response))


  def getSearchablePath(self):
    return "%s%%" %(self.getPath().replace('_', '\_'),)

  def _getSyncMLData(self, syncml_response, min_gid, max_gid):
    """
    Compare data from source with data stored in signature from previous
    synchronization. If there is any change, add command into the syncml
    message

    syncml_response : SyncML message to fill with command
    min_gid = the lower limit for browsing data
    max_gid = the upper limit for browsing data
    """
    syncml_logger.info("getSyncMLData, min %s - max %r" % (min_gid, max_gid,))

    finished = True
    conduit = self.getConduit()

    # Compare gid list to know which data were deleted
    source_gid_list = [x.gid for x in self.z_get_syncml_gid_list(
      strict_min_gid=None,
      min_gid=min_gid,
      max_gid=max_gid,
      path =self.getSearchableSourcePath(),
      limit=None)]

    src = self.z_get_syncml_gid_list(
      src__=1,
      strict_min_gid=None,
      min_gid=min_gid,
      max_gid=max_gid,
      path = self.getSearchablePath(),
      limit=None)

    syncml_logger.info("source %r" % (src,))
    signature_list = [x.gid for x in self.z_get_syncml_gid_list(
      strict_min_gid=None,
      min_gid=min_gid,
      max_gid=max_gid,
      path = self.getSearchablePath(),
      limit=None)]

    signature_set = set(signature_list)
    source_gid_set = set(source_gid_list) # XXX get it with mysql
    deleted_signature_set = signature_set - source_gid_set
    syncml_logger.info("\t---> delete signature are %r from %r - %r"
                       % (deleted_signature_set, signature_set, source_gid_set))
    for gid in deleted_signature_set:
      syncml_response.addDeleteCommand(gid=gid)

    traverse = self.getPortalObject().restrictedTraverse
    object_list = [traverse(x.path) for x in self.z_get_syncml_path_list(
      min_gid=min_gid,
      max_gid=max_gid,
      path=self.getSearchableSourcePath())]

    alert_code = self.getSyncmlAlertCode()
    sync_all = alert_code in ("refresh_from_client_only", "slow_sync")
    # XXX Quick & dirty hack to prevent signature creation, this must be defined
    # on pub/sub instead
    create_signature = alert_code != "refresh_from_client_only"

    if not len(object_list) and (min_gid or max_gid):
      raise ValueError("No object retrieved althoud min/max gid (%s/%s) is provided"
                            % (min_gid, max_gid))

    path_list = []
    for result in object_list:
      object_path = result.getPath()
      # if loop >= max_range:
      #   # For now, maximum object list is always none, so we will never come here !
      #   syncml_logger.warning("...Send too many objects, will split message...")
      #   finished = False
      #   break
      # Get the GID
      document = traverse(object_path)
      gid = self.getGidFromObject(document)
      if not gid:
        raise ValueError("Impossible to compute gid for %s" %(object_path))

      if True: # not loop: # or len(syncml_response) < MAX_LEN:
        # XXX must find a better way to prevent sending
        # no object due to a too small limit
        signature = self.getSignatureFromGid(gid)
        more_data = False
        if signature:
          syncml_logger.debug("signature is %s = %s" %(signature.getRelativeUrl(),
                                                      signature.getValidationState()))
        # For the case it was never synchronized, we have to send everything
        if not signature or sync_all:
          # Either it is the first time we get this object
          # either the synchronization process required
          # to send every data again as if it was never done before
          document_data = conduit.getXMLFromObjectWithId(
            # XXX To be renamed (getDocumentData) independant from format
            document,
            xml_mapping=self.getXmlBindingGeneratorMethodId(),
            context_document=self.getPath())

          if not document_data:
            continue

          if create_signature:
            if not signature:
              signature = self.newContent(portal_type='SyncML Signature',
                                          id=gid,
                                          reference=document.getPath(),
                                          temporary_data=document_data)
              syncml_logger.debug("Created a signature %s for gid = %s, path %s"
                                 % (signature.getPath(), gid, document.getPath()))
            if len(document_data) > MAX_LEN:
              syncml_logger.info("data too big, sending  multiple message")
              more_data = True
              finished = False
              document_data, rest_string = cutXML(document_data, MAX_LEN)
              # Store the remaining data to send it later
              signature.setPartialData(rest_string)
              signature.setPartialAction(ADD_ACTION)
              signature.changeToPartial()
            else:
              # The data will be copied in 'data' property once we get
              # confirmation that the document was well synchronized
              signature.setTemporaryData(document_data)
              signature.doSync()
              syncml_logger.debug("signature %s is syncing"
                                 % (signature.getRelativeUrl(),))

          # Generate the message
          syncml_response.addSyncCommand(
            sync_command=ADD_ACTION,
            gid=gid,
            data=document_data,
            more_data=more_data,
            media_type=conduit.getContentType())

        elif signature.getValidationState() in ('not_synchronized', 'synchronized',
                                                'conflict_resolved_with_merge'):
          # We don't have synchronized this object yet but it has a signature
          xml_object = conduit.getXMLFromObjectWithId(document,
                           xml_mapping=self.getXmlBindingGeneratorMethodId(),
                           context_document=self.getPath())

          if signature.getValidationState() == 'conflict_resolved_with_merge':
            # XXX Why putting confirmation message here
            # Server can get confirmation of sync although it has not yet
            # send its data modification to the client
            # This must be checked against specifications
            syncml_response.addConfirmationMessage(
              source_ref=signature.getId(),
              sync_code='conflict_resolved_with_merge',
              command='Replace')
          syncml_logger.debug("\tMD5 is %s for %s" %((signature.checkMD5(xml_object)),
                                                     signature.getReference()))
          if not signature.checkMD5(xml_object):
            # MD5 checksum tell there is a modification of the object
            if conduit.getContentType() != 'text/xml':
              # If there is no xml, we re-send the whole object
              # XXX this must be managed by conduit ?
              data_diff = xml_object
            else:
              # Compute the diff
              new_document = conduit.replaceIdFromXML(xml_object, 'gid', gid)
              previous_document = conduit.replaceIdFromXML(signature.getData(),
                                                           'gid', gid)
              data_diff = conduit.generateDiff(new_data=new_document,
                                               former_data=previous_document)

            if not data_diff:
              # MD5 Checksum can detect changes like <lang/> != <lang></lang>
              # but Diff generator will return no diff for it
              # in this case, no need to send diff
              if signature.getValidationState() != "synchronized":
                signature.synchronize()
              syncml_logger.debug("signature %s is synchronized"
                                 % (signature.getRelativeUrl(),))
              path_list.append(signature.getPath())
              continue

            # Split data if necessary
            if  len(data_diff) > MAX_LEN:
              syncml_logger.info("data too big, sending multiple messages")
              more_data = True
              finished = False
              data_diff, rest_string = cutXML(data_diff, MAX_LEN)
              signature.setPartialData(rest_string)
              signature.setPartialAction(REPLACE_ACTION)
              if signature.getValidationState() != 'partial':
                signature.changeToPartial()
              syncml_logger.info("signature %s is partial"
                                 % (signature.getRelativeUrl(),))
            else:
              # Store the new representation of the document
              # It will be copy to "data" property once synchronization
              # is confirmed
              signature.setTemporaryData(xml_object)
              signature.doSync()
              syncml_logger.debug("signature %s is syncing"
                                 % (signature.getRelativeUrl(),))

            # Generate the command
            syncml_logger.debug("will send Replace command with %s"
                                % (data_diff,))
            syncml_response.addSyncCommand(
              sync_command=REPLACE_ACTION,
              gid=gid,
              data=data_diff,
              more_data=more_data,
              media_type=conduit.getContentType())

          elif signature.getValidationState() != 'synchronized':
            # We should not have this case when we are in CONFLICT_MERGE
            syncml_logger.debug("signature %s is synchronized"
                               % (signature.getRelativeUrl(),))
            signature.synchronize()

        elif signature.getValidationState() == \
            'conflict_resolved_with_client_command_winning':
          # We have decided to apply the update
          # XXX previous_xml will be geXML instead of getTempXML because
          # some modification was already made and the update
          # may not apply correctly
          xml_update = signature.getPartialData()
          previous_xml_with_gid = conduit.replaceIdFromXML(signature.getData(),
                                                           'gid', gid,
                                                           as_string=False)
          conduit.updateNode(xml=xml_update, object=document,
                             previous_xml=previous_xml_with_gid, force=True,
                             gid=gid,
                             signature=signature,
                             domain=self)
          syncml_response.addConfirmationMessage(
            target_ref=gid,
            sync_code='conflict_resolved_with_client_command_winning',
            command='Replace')
          signature.synchronize()
          syncml_logger.debug("signature %s is synchronized"
                             % (signature.getRelativeUrl(),))

        elif signature.getValidationState() == 'partial':
          # Case of partially sent data
          xml_string = signature.getPartialData()
          # XXX Cutting must be managed by conduit
          # Here it is too specific to XML data
          if len(xml_string) > MAX_LEN:
            syncml_logger.info("Remaining data too big, splitting it...")
            more_data = True
            finished = False
            xml_string = signature.getFirstPdataChunk(MAX_LEN)
          xml_string = etree.CDATA(xml_string.decode('utf-8'))

          syncml_response.addSyncCommand(
            sync_command=signature.getPartialAction(),
            gid=gid,
            data=xml_string,
            more_data=more_data,
            media_type=self.getContentType())

          if not more_data:
            signature.doSync()
            syncml_logger.debug("signature %s is syncing"
                               % (signature.getRelativeUrl(),))
        elif signature.getValidationState() in ('syncing'):
          raise ValueError("Must not get signature in %s state here, signature is %s"
                           % (signature.getValidationState(),
                              signature.getPath(),))

        if signature:
          path_list.append(signature.getPath())

        if not more_data:
          pass
        else:
          syncml_logger.info("Splitting document")
          break
      else:
        syncml_logger.warning("Package is going to be splitted")
        break

    self.SQLCatalog_indexSyncMLDocumentList(path_list)
    syncml_logger.info("_getSyncMLData end with finished %s"
                       % (finished,))
    return finished

  security.declareProtected(Permissions.AccessContentsInformation,
                            'getConduit')
  def getConduit(self):
    """
    Return the conduit object defined
    """
    conduit_name = self.getConduitModuleId()
    return getConduitByName(conduit_name)

  security.declarePrivate('checkCorrectRemoteMessageId')
  def checkCorrectRemoteMessageId(self, message_id):
    """
    Check this is not an already processed message based on its id
    If it is, the response will be resent as we do not want to reprocess
    the same data again XXX Maybe it is possible to be stateless ?

    Use memcache to retrieve the message so that it does not impact scalability
    """
    # XXX To be done
    return True

  security.declareProtected(Permissions.AccessContentsInformation,
                            'getXmlBindingGeneratorMethodId')
  def getXmlBindingGeneratorMethodId(self, default=_MARKER, force=False):
    """
    XXX force parameter must be removed
    Return the xml mapping
    """
    if default is _MARKER:
      return self._baseGetXmlBindingGeneratorMethodId()
    else:
      return self._baseGetXmlBindingGeneratorMethodId(default=default)

  security.declareProtected(Permissions.AccessContentsInformation,
                            'getGidFromObject')
  def getGidFromObject(self, object, encoded=True):
    """
      Returns the object gid
    """
    # first try with new method
    gid_generator = self.getGidGeneratorMethodId("")
    if gid_generator and getattr(self, gid_generator, None):
      raw_gid = getattr(self, gid_generator)(object)
    else:
      # old way using the conduit
      conduit = self.getConduit()
      raw_gid = conduit.getGidFromObject(object)
    if isinstance(raw_gid, unicode):
      raw_gid = raw_gid.encode('ascii', 'ignore')
    if encoded:
      gid = b16encode(raw_gid)
    else:
      gid = raw_gid
    return gid

  security.declareProtected(Permissions.AccessContentsInformation,
                            'getDocumentFromGid')
  def getDocumentFromGid(self, gid):
    """
    Return the document for a given GID
    - First try using the signature which is linked to the document
    - Otherwise use the list method
    """
    if len(gid)%2 != 0:
      # something encode in base 16 is always a even number of number
      # if not, b16decode will failed
      return None
    signature = self.getSignatureFromGid(gid)
    # First look if we do already have the mapping between
    # the id and the gid
    if signature and signature.getReference():
      document = self.getPortalObject().unrestrictedTraverse(
        signature.getReference(), None)
      if document:
        return document
    object_list = self.getDocumentList(gid=b16decode(gid))
    for document in object_list:
      document_gid = self.getGidFromObject(document)
      if document_gid == gid:
        return document
    return None

  security.declareProtected(Permissions.AccessContentsInformation,
                            'getDocumentIdList')
  def getDocumentIdList(self, limit, **search_kw):
    """
    Method called to return the id list sorted within the given limits
    """
    return self.getDocumentList(id_only=True, limit=limit, **search_kw)

  security.declareProtected(Permissions.AccessContentsInformation,
                            'getDocumentList')
  def getDocumentList(self, **kw):
    """
    This returns the list of sub-object corresponding
    to the query
    """
    folder = self.getSourceValue()
    list_method_id = self.getListMethodId()
    if list_method_id and isinstance(list_method_id, str):
      query_method = folder.unrestrictedTraverse(list_method_id, None)
      if query_method:
        try:
          result_list = query_method(context_document=self, **kw)
        except TypeError:
          if not RETRO_COMPATIBLE:
            raise
          else:
            result_list = query_method(**kw)
      else:
        raise KeyError, 'This Subscriber %s provide no list method:%r'\
          % (self.getPath(), list_method_id)
    else:
      raise KeyError, 'This Subscriber %s provide no list method with id:%r'\
        % (self.getPath(), list_method_id)
    return result_list

  security.declareProtected(Permissions.ModifyPortalContent, 'generateNewSessionId')
  def generateNewSessionId(self):
    """
    Generate new session using portal ids
    """
    id_group = ("session_id", self.getRelativeUrl())
    return self.getPortalObject().portal_ids.generateNewId(
      id_group=id_group,
      id_generator="mysql_non_continuous_increasing_non_zodb",
      default=1)

  security.declareProtected(Permissions.ModifyPortalContent, 'getNextMessageId')
  def getNextMessageId(self):
    """
    Generate new message id using portal ids
    This depends on the session id as there is no way to reset it
    """
    return self.getNextMessageIdList(id_count=1)[0]

  security.declareProtected(Permissions.ModifyPortalContent, 'getNextMessageIdList')
  def getNextMessageIdList(self, id_count):
    """
    Generate new message id list using portal ids
    This depends on the session id as there is no way to reset it
    """
    id_group = ("message_id", self.getRelativeUrl(), self.getSessionId())
    return self.getPortalObject().portal_ids.generateNewIdList(
      id_generator="mysql_non_continuous_increasing_non_zodb",
      id_group=id_group, id_count=id_count, default=1)


  security.declareProtected(Permissions.ModifyPortalContent,
                            'createNewAnchor')
  def createNewAnchor(self):
    """
      set a new anchor
    """
    self.setLastAnchor(self.getNextAnchor())
    self.setNextAnchor(buildAnchorFromDate(DateTime()))

  security.declareProtected(Permissions.ModifyPortalContent,
                            'resetAnchorList')
  def resetAnchorList(self):
    """
      reset both last and next anchors
    """
    self.setLastAnchor(NULL_ANCHOR)
    self.setNextAnchor(NULL_ANCHOR)

  security.declareProtected(Permissions.AccessContentsInformation,
                            'getSignatureFromObjectId')
  def getSignatureFromObjectId(self, id):
    """
    return the signature corresponding to the id
    ### Use a reverse dictionary will be usefull
    to handle changes of GIDs
    """
    # XXX very slow
    for signature in self.objectValues():
      document = signature.getSourceValue()
      if document is not None:
        if id == document.getId():
          return signature
    else: # XXX-Aurel : maybe none is expected
      raise KeyError, id

  security.declareProtected(Permissions.AccessContentsInformation,
                            'getSignatureFromGid')
  def getSignatureFromGid(self, gid):
    """
    return the signature corresponding to the gid
    """
    return self._getOb(gid, None)

  security.declareProtected(Permissions.AccessContentsInformation,
                            'getSignatureList')
  @deprecated
  def getSignatureList(self):
    """
      Returns the list of Signatures
    """
    return self.contentValues(portal_type='SyncML Signature')

  security.declareProtected(Permissions.AccessContentsInformation,
                            'hasSignature')
  def hasSignature(self, gid):
    """
      Check if there's a signature with this uid
    """
    return self.getSignatureFromGid(gid) is not None


  security.declareProtected(Permissions.ModifyPortalContent,
                            'resetSignatureList')
  def resetSignatureList(self):
    """
    XXX Method must be renamed as it delete signature and do no
    reset them
    Delete signature in acticities
    XXX Must also be splitted in activity like the real reset
    """
    object_id_list = list(self.getObjectIds())
    object_list_len = len(object_id_list)
    for i in xrange(0, object_list_len, MAX_OBJECTS):
      current_id_list = object_id_list[i:i+MAX_OBJECTS]
      self.activate(activity='SQLQueue',
                    priority=ACTIVITY_PRIORITY).manage_delObjects(current_id_list)

  security.declareProtected(Permissions.AccessContentsInformation,
                            'getConflictList')
  def getConflictList(self, *args, **kw):
    """
    Return the list of all conflicts from all signatures
    """
    conflict_list = []
    for signature in self.objectValues():
      conflict_list.extend(signature.getConflictList())
    return conflict_list


  security.declareProtected(Permissions.ModifyPortalContent,
                            'indexSourceData')
  def indexSourceData(self, client=False):
    """
    Index source data into mysql for ensemble comparison
    This depends on synchronization type
    """
    if (client and self.getSyncmlAlertCode() not in \
       ("one_way_from_server", "refresh_from_server_only")) or \
       (not client and self.getSyncmlAlertCode() not in \
       ("one_way_from_client", "refresh_from_client_only")):

      portal = self.getPortalObject()
      pref = portal.portal_preferences
      # First we must unindex everything
      portal.z_unindex_syncml_data(path=self.getSearchableSourcePath())
      if self.getIsActivityEnabled():
        activate_kw = {
          'activity' : 'SQLQueue',
          'tag' : self.getRelativeUrl(),
          'priority' :ACTIVITY_PRIORITY
        }
        self.getAndIndex(
          callback="SQLCatalog_indexSyncMLDocumentList",
          method_kw={'subscription_path' : self.getRelativeUrl()},
          activate_kw=activate_kw,
          packet_size=pref.getPreferredDocumentRetrievedPerActivityCount(),
          activity_count=pref.getPreferredRetrievalActivityCount(),
        )
      else:
        r = [x.getPath() for x in self.getDocumentList()]
        syncml_logger.info("indexing data from %s : %r" %(self.getPath(), r))
        portal.SQLCatalog_indexSyncMLDocumentList(
          path_list=r[:],
          subscription_path=self.getRelativeUrl())


  security.declareProtected(Permissions.ModifyPortalContent,
                            'getAndActivateResetSignature')
  def getAndActivateResetSignature(self, min_packet_id=0):
    """
    Reset signature by packet (i.e. getAndActivate)
    """
    self.recurseCallMethod(method_id="reset",
                           method_kw={"no_conflict": True},
                           min_depth=1,
                           max_depth=1,
                           activate_kw={'priority': ACTIVITY_PRIORITY,
                                        'tag' : "%s_reset" % self.getPath()})
