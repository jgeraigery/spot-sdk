# Copyright (c) 2020 Boston Dynamics, Inc.  All rights reserved.
#
# Downloading, reproducing, distributing or otherwise using the SDK Software
# is subject to the terms and conditions of the Boston Dynamics Software
# Development Kit License (20191101-BDSDK-SL).

"""Client for the payload service.

This allows client code to write to the robot payload registry.
"""

from __future__ import print_function
import collections
import logging

import bosdyn.api.payload_registration_pb2 as payload_registration_protos
import bosdyn.api.payload_registration_service_pb2_grpc as payload_registration_service

from bosdyn.client.common import (BaseClient, error_factory, handle_unset_status_error,
                                  handle_common_header_errors, handle_lease_use_result_errors)
from bosdyn.client import ResponseError

LOGGER = logging.getLogger('payload_registration_client')


# Define payload-registration-specefic errors
class PayloadRegistrationResponseError(ResponseError):
    """General class of errors for PayloadRegistration service."""


class InvalidPayloadCredentialsError(PayloadRegistrationResponseError):
    """The payload credentials do not match any payload registered to the robot."""


class PayloadNotAuthorizedError(PayloadRegistrationResponseError):
    """The payload is not authorized."""


class PayloadAlreadyExistsError(PayloadRegistrationResponseError):
    """A payload with this GUID is already registered on the robot."""


class PayloadDoesNotExistError(PayloadRegistrationResponseError):
    """A payload with this GUID is not registered on the robot."""


def _get_token(response):
    return response.token


class PayloadRegistrationClient(BaseClient):
    """A client registering payload configs onto the robot."""

    default_service_name = 'payload-registration'
    service_type = 'bosdyn.api.PayloadRegistrationService'

    def __init__(self):
        super(PayloadRegistrationClient,
              self).__init__(payload_registration_service.PayloadRegistrationServiceStub)

    def register_payload(self, payload, secret, **kw_args):
        """Register a payload to the robot.

        Args:
          payload:              The payload protobuf message to register.
          secret:               Unique string to verify payload.
          kw_args:              Extra arguments to pass to grpc call invocation.

        Raises:
          RpcError: Problem communicating with the robot.
          PayloadAlreadyExistsError: A payload with the provided GUID
            already exists.
          PayloadRegistrationResponseError: Something went wrong during the payload registration.
        """
        request = payload_registration_protos.RegisterPayloadRequest()
        request.payload.CopyFrom(payload)
        if secret:
            request.payload_secret = secret
        return self.call(self._stub.RegisterPayload, request,
                         error_from_response=_payload_registration_error, **kw_args)

    def register_payload_async(self, payload, secret, **kw_args):
        """Register a payload to the robot.

        Args:
          payload:              The payload protobuf message to register.
          secret:               Unique string to verify payload.
          kw_args:              Extra arguments to pass to grpc call invocation.

        Raises:
          RpcError: Problem communicating with the robot.
          PayloadAlreadyExistsError: A payload with the provided GUID
            already exists.
          PayloadRegistrationResponseError: Something went wrong during the payload registration.
        """
        request = payload_registration_protos.RegisterPayloadRequest()
        request.payload.CopyFrom(payload)
        if secret:
            request.payload_secret = secret
        return self.call_async(self._stub.RegisterPayload, request,
                               error_from_response=_payload_registration_error, **kw_args)

    def update_payload_version(self, guid, secret, updated_version, **kw_args):
        """Update an existing payload's version on the robot.

        Args:
          guid:                 The GUID of the payload to update.
          secret:               Secret of the payload to update.
          updated_version:      The new version to set this payload to.
          kw_args:              Extra arguments to pass to grpc call invocation.

        Raises:
          RpcError: Problem communicating with the robot.
          PayloadDoesNotExistError: A payload with the provided GUID does not exist.
          InvalidPayloadCredentialsError: The GUID + secret does not match an existing payload.
          PayloadRegistrationResponseError: Something went wrong during the payload registration.
        """
        request = payload_registration_protos.UpdatePayloadVersionRequest()
        request.payload_guid = guid
        request.payload_secret = secret
        request.updated_version.CopyFrom(updated_version)
        return self.call(self._stub.UpdatePayloadVersion, request,
                         error_from_response=_update_payload_version_error, **kw_args)

    def update_payload_version_async(self, guid, secret, updated_version, **kw_args):
        """Update an existing payload on the robot.

        Args:
          guid:                 The GUID of the payload to update.
          secret:               Secret of the payload to update.
          updated_version:      The new version to set this payload to.
          kw_args:              Extra arguments to pass to grpc call invocation.

        Raises:
          RpcError: Problem communicating with the robot.
          PayloadDoesNotExistError: A payload with the provided GUID does not exist.
          InvalidPayloadCredentialsError: The GUID + secret does not match an existing payload.
          PayloadRegistrationResponseError: Something went wrong during the payload registration.
        """
        request = payload_registration_protos.UpdatePayloadVersionRequest()
        request.payload_guid = guid
        request.payload_secret = secret
        request.updated_version.CopyFrom(updated_version)
        return self.call_async(self._stub.UpdatePayloadVersion, request,
                         error_from_response=_update_payload_version_error, **kw_args)

    def get_payload_auth_token(self, guid, secret, **kw_args):
        """Request a limited-access auth token for a payload.
        
        Getting the auth token requires payload to be authorized via the web console.

        Args:
          guid:                 The GUID of the registered payload requesting the token.
          secret:               The secret of the registed payload requesting the token.
          kw_args:              Extra arguments to pass to grpc call invocation.

        Returns:
          A limited-access user token for the robot
        
        Raises:
          RpcError: Problem communicating with the robot.
          PayloadNotAuthorizedError: The payload with the provided GUID is
            not authorized and cannot request a token.
          InvalidPayloadCredentialsError: The provided GUID + secret combo
            does not match any existing payload.
          PayloadRegistrationResponseError: Something went wrong during the payload registration.
        """
        request = payload_registration_protos.GetPayloadAuthTokenRequest(
            payload_guid=guid, payload_secret=secret)
        return self.call(self._stub.GetPayloadAuthToken, request, value_from_response=_get_token,
                         error_from_response=_get_payload_auth_token_error, **kw_args)


# Associate proto status errors to python client errors for RegisterPayload
_REGISTER_PAYLOAD_STATUS_TO_ERROR = collections.defaultdict(lambda: (ResponseError, None))
_REGISTER_PAYLOAD_STATUS_TO_ERROR.update({
    payload_registration_protos.RegisterPayloadResponse.STATUS_OK: (None, None),
    payload_registration_protos.RegisterPayloadResponse.STATUS_ALREADY_EXISTS:
    (PayloadAlreadyExistsError, PayloadAlreadyExistsError.__doc__),
})


# Function to parse all types of errors from payload registration response
@handle_common_header_errors
@handle_unset_status_error(unset='STATUS_UNKNOWN')
def _payload_registration_error(response):
    """Return a custom exception based on response, None if no error."""
    return error_factory(
        response, response.status,
        status_to_string=payload_registration_protos.RegisterPayloadResponse.Status.Name,
        status_to_error=_REGISTER_PAYLOAD_STATUS_TO_ERROR)


# Associate proto status errors to python client errors for UpdatePayloadVersion
_UPDATE_PAYLOAD_VERSION_STATUS_TO_ERROR = collections.defaultdict(lambda: (ResponseError, None))
_UPDATE_PAYLOAD_VERSION_STATUS_TO_ERROR.update({
    payload_registration_protos.UpdatePayloadVersionResponse.STATUS_OK: (None, None),
    payload_registration_protos.UpdatePayloadVersionResponse.STATUS_DOES_NOT_EXIST:
    (PayloadDoesNotExistError, PayloadDoesNotExistError.__doc__),
    payload_registration_protos.UpdatePayloadVersionResponse.STATUS_INVALID_CREDENTIALS:
    (InvalidPayloadCredentialsError, InvalidPayloadCredentialsError.__doc__),
})


# Function to parse all types of errors from get update payload version response
@handle_common_header_errors
@handle_unset_status_error(unset='STATUS_UNKNOWN')
def _update_payload_version_error(response):
    """Return a custom exception based on response, None if no error."""
    return error_factory(
        response, response.status,
        status_to_string=payload_registration_protos.UpdatePayloadVersionResponse.Status.Name,
        status_to_error=_UPDATE_PAYLOAD_VERSION_STATUS_TO_ERROR)


# Associate proto status errors to python client errors for GetPayloadAuthToken
_GET_PAYLOAD_AUTH_TOKEN_STATUS_TO_ERROR = collections.defaultdict(lambda: (ResponseError, None))
_GET_PAYLOAD_AUTH_TOKEN_STATUS_TO_ERROR.update({
    payload_registration_protos.GetPayloadAuthTokenResponse.STATUS_OK: (None, None),
    payload_registration_protos.GetPayloadAuthTokenResponse.STATUS_INVALID_CREDENTIALS:
    (InvalidPayloadCredentialsError, InvalidPayloadCredentialsError.__doc__),
    payload_registration_protos.GetPayloadAuthTokenResponse.STATUS_PAYLOAD_NOT_AUTHORIZED:
    (PayloadNotAuthorizedError, PayloadNotAuthorizedError.__doc__),
})


# Function to parse all types of errors from get payload auth token response
@handle_common_header_errors
@handle_unset_status_error(unset='STATUS_UNKNOWN')
def _get_payload_auth_token_error(response):
    """Return a custom exception based on response, None if no error."""
    return error_factory(
        response, response.status,
        status_to_string=payload_registration_protos.GetPayloadAuthTokenResponse.Status.Name,
        status_to_error=_GET_PAYLOAD_AUTH_TOKEN_STATUS_TO_ERROR)
