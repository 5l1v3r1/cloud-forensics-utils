# -*- coding: utf-8 -*-
# Copyright 2020 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for the azure module - common.py"""

import os
import typing
import unittest
import mock

from libcloudforensics import errors
from libcloudforensics.providers.azure.internal import common
from tests.providers.azure import azure_mocks


class AZCommonTest(unittest.TestCase):
  """Test Azure common file."""
  # pylint: disable=line-too-long

  @typing.no_type_check
  def testGenerateDiskName(self):
    """Test that disk names are correclty generated.

    The disk name must comply with the following RegEx: ^[\\w]{1,80}$
        i.e., it must be between 1 and 80 chars and be within [a-zA-Z0-9].
    """
    disk_name = common.GenerateDiskName(azure_mocks.FAKE_SNAPSHOT)
    self.assertEqual('fake_snapshot_name_c4a46ad7_copy', disk_name)

    disk_name = common.GenerateDiskName(
        azure_mocks.FAKE_SNAPSHOT, disk_name_prefix='prefix')
    self.assertEqual('prefix_fake_snapshot_name_c4a46ad7_copy', disk_name)

  @mock.patch('msrestazure.azure_active_directory.ServicePrincipalCredentials.__init__')
  @typing.no_type_check
  def testGetCredentials(self, mock_azure_credentials):
    """Test that credentials are parsed correctly / found."""

    mock_azure_credentials.return_value = None

    # If all environment variables are defined, things should work correctly
    os.environ['AZURE_SUBSCRIPTION_ID'] = 'fake-subscription-id'
    os.environ["AZURE_CLIENT_ID"] = 'fake-client-id'
    os.environ["AZURE_CLIENT_SECRET"] = 'fake-client-secret'
    os.environ["AZURE_TENANT_ID"] = 'fake-tenant-id'

    subscription_id, _ = common.GetCredentials()
    self.assertEqual('fake-subscription-id', subscription_id)
    mock_azure_credentials.assert_called_with(
        'fake-client-id', 'fake-client-secret', tenant='fake-tenant-id')

    # If an environment variable is missing, a RuntimeError should be raised
    del os.environ['AZURE_SUBSCRIPTION_ID']
    with self.assertRaises(errors.CredentialsConfigurationError) as error:
      _, _ = common.GetCredentials()
      mock_azure_credentials.assert_not_called()
    self.assertEqual(
        'Please make sure you defined the following environment variables: '
        '[AZURE_SUBSCRIPTION_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, '
        'AZURE_TENANT_ID].', str(error.exception))

    # If a profile name is passed to the method, then it will look for a
    # credential file (default path being ~/.azure/credentials.json). We can
    # set a particular path by setting the AZURE_CREDENTIALS_PATH variable.

    # If the file is not a valid json file, should raise a ValueError
    os.environ['AZURE_CREDENTIALS_PATH'] = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.realpath(__file__))))), azure_mocks.STARTUP_SCRIPT)
    with self.assertRaises(errors.InvalidFileFormatError) as error:
      _, _ = common.GetCredentials(profile_name='foo')
      mock_azure_credentials.assert_not_called()
    self.assertEqual(
        'Could not decode JSON file. Please verify the file format: Expecting '
        'value: line 1 column 1 (char 0)', str(error.exception))

    # If the file is correctly formatted, then things should work correctly
    os.environ['AZURE_CREDENTIALS_PATH'] = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.realpath(__file__))))), azure_mocks.JSON_FILE)
    subscription_id, _ = common.GetCredentials(
        profile_name='test_profile_name')
    self.assertEqual(
        'fake-subscription-id-from-credential-file', subscription_id)
    mock_azure_credentials.assert_called_with(
        'fake-client-id-from-credential-file',
        'fake-client-secret-from-credential-file',
        tenant='fake-tenant-id-from-credential-file')

    # If the profile name does not exist, should raise a ValueError
    with self.assertRaises(errors.CredentialsConfigurationError) as error:
      _, _ = common.GetCredentials(profile_name='foo')
      mock_azure_credentials.assert_not_called()
    self.assertEqual(
        'Profile name foo not found in credentials file {0:s}'.format(
            os.environ['AZURE_CREDENTIALS_PATH']), str(error.exception))

    # If the profile name exists but there are missing entries, should raise
    # a ValueError
    with self.assertRaises(errors.CredentialsConfigurationError) as error:
      _, _ = common.GetCredentials(profile_name='incomplete_profile_name')
      mock_azure_credentials.assert_not_called()
    self.assertEqual(
        'Profile name incomplete_profile_name not found in credentials file '
        '{0:s}'.format(
            os.environ['AZURE_CREDENTIALS_PATH']), str(error.exception))
