# Copyright (C) 2012-2013  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#

from __future__ import absolute_import
try:
    from unittest import mock
except ImportError:
    from tests import mock
from tests import support
import dnf.cli.output
import dnf.transaction
import unittest
from tests.support import PycompTestCase

LIST_TRANSACTION_OUTPUT=u"""
================================================================================
 Package           Arch              Version           Repository          Size
================================================================================
Upgrading:
 pepper            x86_64            20-1              updates              0  
     replacing  hole.x86_64 1-1

Transaction Summary
================================================================================
Upgrade  1 Package
"""

class OutputTest(PycompTestCase):
    @staticmethod
    def _keyboard_interrupt(*ignored):
        raise KeyboardInterrupt

    @staticmethod
    def _eof_error(*ignored):
        raise EOFError

    def setUp(self):
        self.output = dnf.cli.output.Output()
        self.output.conf = support.FakeConf()

    @mock.patch('dnf.cli.output._term_width', return_value=80)
    def test_list_transaction(self, _term_width):
        sack = support.MockYumBase('updates').sack
        q = sack.query().filter(name='pepper')
        i = q.installed()[0]
        u = q.available()[0]
        obs = sack.query().filter(name='hole').installed()[0]

        transaction = dnf.transaction.Transaction()
        transaction.add_upgrade(u, i, [obs])
        self.output._transaction = transaction
        self.assertEqual(self.output.list_transaction(), LIST_TRANSACTION_OUTPUT)

    @mock.patch('dnf.i18n.ucd_input')
    def test_userconfirm(self, input_fnc):
        # with defaultyes==False
        input_fnc.return_value = 'y'
        self.assertTrue(self.output.userconfirm())
        self.assertEqual(input_fnc.call_args, mock.call(u'Is this ok [y/N]: '))

        input_fnc.return_value = 'n'
        self.assertFalse(self.output.userconfirm())

        input_fnc.return_value = ''
        self.assertFalse(self.output.userconfirm())

        input_fnc.side_effect = self._keyboard_interrupt
        input_fnc.return_value = 'y'
        self.assertFalse(self.output.userconfirm())

        input_fnc.side_effect = self._eof_error
        self.assertFalse(self.output.userconfirm())

        # with defaultyes==True
        self.output.conf.defaultyes = True
        input_fnc.side_effect = None
        input_fnc.return_value = ''
        self.assertTrue(self.output.userconfirm())

        input_fnc.side_effect = self._keyboard_interrupt
        input_fnc.return_value = ''
        self.assertFalse(self.output.userconfirm())

        input_fnc.side_effect = self._eof_error
        self.assertTrue(self.output.userconfirm())

    def _to_unicode_mock(str):
        return {'y': 'a', 'yes': 'ano', 'n': 'e', 'no': 'ee'}.get(str, str)

    @mock.patch('dnf.cli.output._', _to_unicode_mock)
    @mock.patch('dnf.i18n.ucd_input')
    def test_userconfirm_translated(self, input_fnc):
        input_fnc.return_value = 'ee'
        self.assertFalse(self.output.userconfirm())

        input_fnc.return_value = 'ano'
        self.assertTrue(self.output.userconfirm())

    class _InputGenerator(object):
        INPUT=['haha', 'dada', 'n']

        def __init__(self):
            self.called = 0

        def __call__(self, msg):
            ret = self.INPUT[self.called]
            self.called += 1
            return ret

    def test_userconfirm_bad_input(self):
        input_fnc = self._InputGenerator()
        with mock.patch('dnf.i18n.ucd_input', input_fnc):
            self.assertFalse(self.output.userconfirm())
        self.assertEqual(input_fnc.called, 3)

PKGS_IN_GROUPS_OUTPUT = u"""\

Group: Pepper's
 Mandatory Packages:
   hole
   lotus
"""

PKGS_IN_GROUPS_VERBOSE_OUTPUT = u"""\

Group: Pepper's
 Group-Id: Peppers
 Mandatory Packages:
   hole-1-1.x86_64                                                       @System
   lotus-3-16.i686                                                       main   
"""

class GroupOutputTest(unittest.TestCase):
    def setUp(self):
        base = support.MockYumBase('main')
        base.read_mock_comps(support.COMPS_PATH)
        output = dnf.cli.output.Output()
        output.conf = support.FakeConf()
        output.sack = base.sack

        self.base = base
        self.output = output

    @mock.patch('dnf.cli.output._term_width', return_value=80)
    def test_group_info(self, _term_width):
        group = self.base.comps.group_by_pattern('Peppers')
        with support.patch_std_streams() as (stdout, stderr):
            self.output.displayPkgsInGroups(group)
        self.assertEqual(stdout.getvalue(), PKGS_IN_GROUPS_OUTPUT)

    @mock.patch('dnf.cli.output._term_width', return_value=80)
    def test_group_verbose_info(self, _term_width):
        group = self.base.comps.group_by_pattern('Peppers')
        self.output.conf.verbose = True
        with support.patch_std_streams() as (stdout, stderr):
            self.output.displayPkgsInGroups(group)
        self.assertEqual(stdout.getvalue(), PKGS_IN_GROUPS_VERBOSE_OUTPUT)
