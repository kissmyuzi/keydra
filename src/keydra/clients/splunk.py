import splunklib.client as splunkclient
from splunklib.binding import HTTPError


class SplunkClient(object):
    def __init__(self, username, password, host, verify, port=8089):
        '''
        Initializes a Splunk client

        :param username: Username used to connect
        :type username: :class:`string`
        :param password: Password to connect
        :type password: :class:`passwd`
        :param host: The host to connect to
        :type host: :class:`string`
        :param port: The port to use
        :type port: :class:`string`
        :param verify: Verify TLS
        :type verify: :class:`bool`
        '''
        self._service = splunkclient.Service(
            host=host,
            port=port,
            username=username,
            password=password,
            verify=verify
        )
        self._service.login()

    def update_app_config(self, app, path, obj, data):
        '''
        Updates the config of a Splunk app. Will create the
        config entry if it does not already exist.

        :param app: The app context
        :type app: :class:`string`
        :param path: The path to the config object
        :type path: :class:`path`
        :param obj: The config object to update/create
        :type obj: :class:`string`
        :param data: Additional post data
        :type data: :class:`dict`

        :returns: Resulting HTTP status code of the operation
        :rtype: :class:`int`
        '''
        # First check the app is actually installed!
        if self.app_exists(app) is not True:
            raise AppNotInstalledException(
                'App {} not installed on Splunk '
                'host {}'.format(
                    app,
                    self._service.host
                )
            )

        # Try to update the object, throws a HTTPError if fails
        post_data = dict(**data)
        try:
            attempt = self._service.post(
                '/servicesNS/nobody/{app}/'
                '{path}/{object}'.format(
                    app=app,
                    path=path,
                    object=obj
                ),
                **post_data
            )

        except HTTPError as error:
            # We could be here because the object doesn't exist
            # or some other error
            # TODO: Find some way to massage the Splunk API to make this
            #       more robust with status codes than string matching
            if 'does not exist' in str(error.body):
                # Object does not exist, add name and create
                post_data['name'] = obj
                attempt = self._service.post(
                    '/servicesNS/nobody/{app}/'
                    '{path}/{object}'.format(
                        app=app,
                        path=path,
                        object=obj
                    ),
                    **post_data
                )
            else:
                # Something else went wrong
                raise Exception(
                    'Error updating Splunk app {} on '
                    'host {}: {}'.format(
                        app,
                        self._service.host,
                        error
                    )
                )

        return attempt.status

    def update_app_storepass(self, app, username, password, realm=None):
        '''
        Updates a Splunk app storage password. Will create the
        config entry if it does not already exist.

        :param app: The app context
        :type app: :class:`string`
        :param obj: The config object to update/create
        :type obj: :class:`string`
        :param data: Additional post data
        :type data: :class:`dict`

        :returns: Resulting HTTP status code of the operation
        :rtype: :class:`int`
        '''
        if not realm:
            realm = ''

        # First check the app is actually installed!
        if self.app_exists(app) is not True:
            raise AppNotInstalledException(
                'App {} not installed on Splunk '
                'host {}'.format(
                    app,
                    self._service.host
                )
            )

        post_data = {
            'name': username,
            'password': password,
            'realm': realm
        }

        # Craft our URL based on whether the password already exists
        try:
            self._service.get(
                '/servicesNS/nobody/{}/'
                'storage/passwords/{}'.format(app, username)
            )
            url = '/servicesNS/nobody/{}/storage/passwords/{}'.format(
                app,
                username
            )
            post_data.pop('name', None)
            post_data.pop('realm', None)

        except HTTPError:
            url = '/servicesNS/nobody/{}/storage/passwords'.format(app)

        try:
            attempt = self._service.post(url, **post_data)

        except HTTPError as error:
            raise Exception(
                'Error updating Splunk app {} on '
                'host {}: {}'.format(
                    app,
                    self._service.host,
                    error
                )
            )

        return attempt.status

    def app_exists(self, appname):
        '''
        Check if a Splunk app exists

        :param appname: The app name to check for
        :type app: :class:`string`

        :returns: Result of check, True or False
        :rtype: :class:`bool`
        '''
        matching_apps = len(
            self._service.apps.list(search='name={}'.format(appname))
        )
        return matching_apps > 0

    def change_passwd(self, username, oldpasswd, newpasswd):
        '''
        Update a Splunk user account password

        :param username: The username of the account
        :type username: :class:`string`
        :param oldpasswd: The current password of the account
        :type oldpasswd: :class:`passwd`
        :param newpasswd: The new password to change to
        :type newpasswd: :class:`passwd`

        :returns: True if successful
        :rtype: :class:`bool`
        '''
        attempt = self._service.post(
            "/services/authentication/users/{}".format(username),
            password=newpasswd,
            oldpassword=oldpasswd
        )

        if attempt.status != 200:
            raise Exception(
                'Error rotating user {} on Splunk host '
                '{}'.format(username, self._service.host)
            )

        return True


class AppNotInstalledException(Exception):
    pass