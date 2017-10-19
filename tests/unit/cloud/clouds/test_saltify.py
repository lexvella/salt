# -*- coding: utf-8 -*-
'''
    :codeauthor: :email:`Alexander Schwartz <alexander.schwartz@gmx.net>`
'''

# Import Python libs
from __future__ import absolute_import

# Import Salt Testing Libs
from tests.support.mixins import LoaderModuleMockMixin
from tests.support.unit import skipIf, TestCase
from tests.support.mock import MagicMock, NO_MOCK, NO_MOCK_REASON, patch, ANY


# Import Salt Libs
import salt.client
from salt.cloud.clouds import saltify

TEST_PROFILES = {
    'testprofile1': NotImplemented,
    'testprofile2': {  # this profile is used in test_saltify_destroy()
                     'ssh_username': 'fred',
                     'remove_config_on_destroy': False,  # expected for test
                     'shutdown_on_destroy': True  # expected value for test
                     }
    }
TEST_PROFILE_NAMES = ['testprofile1', 'testprofile2']


@skipIf(NO_MOCK, NO_MOCK_REASON)
class SaltifyTestCase(TestCase, LoaderModuleMockMixin):
    '''
    Test cases for salt.cloud.clouds.saltify
    '''
    LOCAL_OPTS = {
        'providers': {
            'sfy1': {
                'saltify': {
                    'driver': 'saltify',
                    'profiles': TEST_PROFILES
                    }
                },
            },
        'profiles': TEST_PROFILES,
        'sock_dir': '/var/sockxxx',
        'transport': 'tcp',
        }

    def setup_loader_modules(self):
        saltify_globals = {
                '__active_provider_name__': '',
                '__utils__': {
                    'cloud.bootstrap': MagicMock(),
                    'cloud.fire_event': MagicMock(),
                    },
                '__opts__': self.LOCAL_OPTS,
                }
        return {saltify: saltify_globals}

    def test_create_no_deploy(self):
        '''
        Test if deployment fails. This is the most basic test as saltify doesn't contain much logic
        '''
        with patch('salt.cloud.clouds.saltify._verify', MagicMock(return_value=True)):
            vm = {'deploy':  False,
                  'driver': 'saltify',
                  'name': 'dummy'
                  }
            self.assertTrue(saltify.create(vm))

    def test_create_and_deploy(self):
        '''
        Test if deployment can be done.
        '''
        mock_cmd = MagicMock(return_value=True)
        with patch.dict(
            'salt.cloud.clouds.saltify.__utils__',
            {'cloud.bootstrap': mock_cmd}):
            vm_ = {'deploy':  True,
                  'driver': 'saltify',
                  'name': 'testprofile2',
                 }
            result = saltify.create(vm_)
            mock_cmd.assert_called_once_with(vm_, ANY)
            self.assertTrue(result)

    def test_avail_locations(self):
        '''
        Test the avail_locations will always return {}
        '''
        self.assertEqual(saltify.avail_locations(), {})

    def test_avail_sizes(self):
        '''
        Test the avail_sizes will always return {}
        '''
        self.assertEqual(saltify.avail_sizes(), {})

    def test_avail_images(self):
        '''
        Test the avail_images will return profiles
        '''
        testlist = list(TEST_PROFILE_NAMES)  # copy
        self.assertEqual(
            saltify.avail_images()['Profiles'].sort(),
            testlist.sort())

    def test_list_nodes(self):
        '''
        Test list_nodes will return required fields only
        '''
        testgrains = {
            'nodeX1': {
                'id': 'nodeX1',
                'ipv4': [
                    '127.0.0.1', '192.1.2.22', '172.16.17.18'],
                'ipv6': [
                    '::1', 'fdef:bad:add::f00', '3001:DB8::F00D'],
                'salt-cloud': {
                    'driver': 'saltify',
                    'provider': 'saltyfy',
                    'profile': 'testprofile2'
                   },
                'extra_stuff': 'does not belong'
                }
            }
        expected_result = {
            'nodeX1': {
                'id': 'nodeX1',
                'image': 'testprofile2',
                'private_ips': [
                    '172.16.17.18', 'fdef:bad:add::f00'],
                'public_ips': [
                    '192.1.2.22', '3001:DB8::F00D'],
                'size': '',
                'state': 'running'
                }
            }
        mm_cmd = MagicMock(return_value=testgrains)
        lcl = salt.client.LocalClient()
        lcl.cmd = mm_cmd
        with patch('salt.client.LocalClient', return_value=lcl):
            self.assertEqual(
                saltify.list_nodes(),
                expected_result)

    def test_saltify_reboot(self):
        mm_cmd = MagicMock(return_value=True)
        lcl = salt.client.LocalClient()
        lcl.cmd = mm_cmd
        with patch('salt.client.LocalClient', return_value=lcl):
            result = saltify.reboot('nodeS1', 'action')
            mm_cmd.assert_called_with('nodeS1', 'system.reboot')
            self.assertTrue(result)

    def test_saltify_destroy(self):
        # destroy calls local.cmd several times and expects
        # different results, so we will provide a list of
        # results. Each call will get the next value.
        # NOTE: this assumes that the call order never changes,
        # so to keep things simple, we will not use remove_config...
        result_list = [
                {'nodeS1': {  # first call is grains.get
                    'driver': 'saltify',
                    'provider': 'saltify',
                    'profile': 'testprofile2'}
                },
                #  Note:
                #    testprofile2 has remove_config_on_destroy: False
                #    and shutdown_on_destroy: True
                {'nodeS1':  # last call shuts down the minion
                     'a system.shutdown worked message'},
            ]
        mm_cmd = MagicMock(side_effect=result_list)
        lcl = salt.client.LocalClient()
        lcl.cmd = mm_cmd
        with patch('salt.client.LocalClient', return_value=lcl):
            result = saltify.destroy('nodeS1', 'action')
            mm_cmd.assert_called_with('nodeS1', 'system.shutdown')
            self.assertTrue(result)
