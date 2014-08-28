##############################################################################
# Copyright (c) 2014 Nexedi SA and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
##############################################################################

from Products.ERP5.Document.ERP5ProjectUnitTestDistributor import ERP5ProjectUnitTestDistributor

from AccessControl import ClassSecurityInfo
from Products.ERP5Type import Permissions
import json

class DREAMSimulationDistributor(ERP5ProjectUnitTestDistributor):
  security = ClassSecurityInfo()
  security.declareObjectProtected(Permissions.AccessContentsInformation)

  security.declarePublic("getTestType")
  def getTestType(self, batch_mode=0):
    """getTestType : return a string defining the type of tests
    """
    return 'DREAMSimulation'
    
    
  security.declarePublic("requestSimulationRun")
  def requestSimulationRun(self, scenario_list):
    """Request to run a list of scenarios, to be called by ManPy during ACO
    
    This will create a planned simulation run document with lines and returns a job_id to the caller
    The testnodes will start the simulation run and start the lines one by one, and stop when posting back the result.
    The last testnode will mark the simulation run as completed.
    
    The caller will getJobResult with this job_id until the simulation run is finished.
    """
    tr = self.getPortalObject().test_result_module.newContent(
      portal_type='Test Result',
      title='DREAM Simulation Run',
    )
    for i, scenario in enumerate(scenario_list):
      tr.newContent(
        portal_type='Test Result Line',
        dream_scenario=scenario,
        int_index=i)
    
    tr.start()
    return tr.getId()
  
  security.declarePublic('getJobResult')
  def getJobResult(self, job_id):
    " "
    test_result = self.getPortalObject().test_result_module._getOb(job_id)
    if test_result.getSimulationState() != 'stopped':
      return
    
    return [test_result_line.getProperty('dream_output')
            for test_result_line in test_result.contentValues()]
  
  security.declarePublic('createTestResult')
  def createTestResult(self, name, revision, test_name_list, allow_restart,
                       test_title=None, node_title=None, project_title=None):
    """Overriden not to lookup project and not to create test result because it's created by requestSimulationRun
    """
    self.log('DREAMSimulationDistributor.createTestResult', 0, (name, revision, test_title, project_title))
    portal = self.getPortalObject()
    if test_title is None:
      test_title = name
    
    def createNode(test_result, node_title):
      if node_title is not None:
        node = self._getTestResultNode(test_result, node_title)
        if node is None:
          node = test_result.newContent(
              portal_type='Test Result Node',
              title=node_title)
          node.start()
    
    def createTestResultLineList(test_result, test_name_list):
      duration_list = []
      previous_test_result_list = portal.test_result_module.searchFolder(
             title='="%s"' % test_result.getTitle(),
             sort_on=[('creation_date','descending')],
             simulation_state=('stopped', 'public_stopped'),
             limit=1)
      if len(previous_test_result_list):
        previous_test_result = previous_test_result_list[0].getObject()
        for line in previous_test_result.objectValues():
          if line.getSimulationState() in ('stopped', 'public_stopped'):
            duration_list.append((line.getTitle(),line.getProperty('duration')))
      duration_list.sort(key=lambda x: -x[1])
      sorted_test_list = [x[0] for x in duration_list]
      # Sort tests by name to have consistent numbering of test result line on
      # a test suite.
      for test_name in sorted(test_name_list):
        index = 0
        if sorted_test_list:
          try:
            index = sorted_test_list.index(test_name)
          except ValueError:
            pass
        line = test_result.newContent(portal_type='Test Result Line',
                                      title=test_name,
                                      int_index=index)
    
    reference_list_string = None
    if type(revision) is str and '=' in revision:
      reference_list_string = revision
      int_index, reference = None, revision
    elif type(revision) is str:
      # backward compatibility
      int_index, reference = revision, None
    else:
      # backward compatibility
      int_index, reference = revision
    result_list = portal.test_result_module.searchFolder(
                         portal_type="Test Result",
                         title='="%s"' % test_title,
                         sort_on=(("creation_date","descending"),),
                         limit=1)
    if result_list:
      test_result = result_list[0].getObject()
      if test_result is not None:
        last_state = test_result.getSimulationState()
        last_revision = str(test_result.getIntIndex()) # XXX we don't need that 
        
        if last_state == 'started':
          createNode(test_result, node_title)
          reference = test_result.getReference()
          if reference_list_string:
            last_revision = reference
          elif reference:
            last_revision = last_revision, reference
          if len(test_result.objectValues(portal_type="Test Result Line")) == 0 \
              and len(test_name_list):
            test_result.serialize() # prevent duplicate test result lines
            createTestResultLineList(test_result, test_name_list)
          return test_result.getRelativeUrl(), last_revision
          
        if last_state in ('stopped', 'public_stopped'):
          if reference_list_string is not None:
            if reference_list_string == test_result.getReference() \
                and not allow_restart:
              return
          elif last_revision == int_index and not allow_restart:
            return

    assert 0, "Test result should already be created"
    test_result = portal.test_result_module.newContent(
      portal_type='Test Result',
      title=test_title,
      reference=reference,
      is_indexable=False)

    if int_index is not None:
      test_result._setIntIndex(int_index)
    if project_title is not None:
      project_list = portal.portal_catalog(portal_type='Project',
                                           title='="%s"' % project_title)
      if len(project_list) != 1:
        raise ValueError('found this list of project : %r for title %r' % \
                      ([x.path for x in project_list], project_title))
      test_result._setSourceProjectValue(project_list[0].getObject())
    test_result.updateLocalRolesOnSecurityGroups() # XXX
    test_result.start()
    del test_result.isIndexable
    test_result.immediateReindexObject()
    self.serialize() # prevent duplicate test result
    # following 2 functions only call 'newContent' on test_result
    createTestResultLineList(test_result, test_name_list)
    createNode(test_result, node_title)
    return test_result.getRelativeUrl(), revision

  security.declarePublic("startTestSuite")
  def saveDREAMSimulationResult(self, test_result_line, output):
    '''Save DREAM simulation result'''
    test_result_line = self.getPortalObject().unrestrictedTraverse(test_result_line)
    test_result_line.setProperty('dream_output', output)
    test_result_line.stop()
    test_result = test_result_line.getParentValue()

    for test_result_line in test_result.contentValues(
                                portal_type='Test Result Line'):
      if test_result_line.getSimulationState() != 'stopped':
        return

    # everything finished.
    test_result.stop()
 
  security.declarePublic("startTestSuite")
  def startTestSuite(self, title, computer_guid='unknown', batch_mode=0, **kw):
    """startTestSuite : subscribe node + return testsuite list to the master. XXX what is a master ?
    """
    ERP5ProjectUnitTestDistributor.subscribeNode(self, title=title, computer_guid=computer_guid, batch_mode=batch_mode)
    
    dream_repo = {'branch': 'dream',
                  'buildout_section_id': 'slapos',
                  'url': 'http://git.erp5.org/repos/slapos.git',
                  'profile_path': 'software/dream/software.cfg'}

    result_list = self.getPortalObject().portal_catalog.unrestrictedSearchResults(
                         portal_type="Test Result",
                         title='DREAM Simulation Run', # XXX use exact match
                         sort_on=(("creation_date","descending"),), simulation_state='started',
                         limit=1)
    if result_list:
      test_result = result_list[0].getObject()
      for scenario in test_result.contentValues(portal_type='Test Result Line'):
        if scenario.getSimulationState() == 'draft':
          scenario.start(comment="OK")
          return json.dumps([{'project_title': 'DREAM Simulation Distribution Project',
              'test_suite_reference': 'dream_runner',
              'test_suite_title': 'DREAM Simulation Run',
              'test_result_line_id': scenario.getId(),
              'scenario': scenario.getProperty('dream_scenario'),
              'vcs_repository_list': [ dream_repo] }])

    # always return the same test_suite_reference otherwise software is removed.
    return json.dumps([{'project_title': 'DREAM Simulation Distribution Project',
              'test_suite_reference': 'dream_runner',
              'test_suite_title': 'DREAM Simulation Run',
              'scenario': None,
              'vcs_repository_list': [ dream_repo] }])
              
