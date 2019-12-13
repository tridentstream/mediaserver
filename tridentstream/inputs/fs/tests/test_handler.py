# import os
# import shutil

# from django.contrib.auth.models import User
# from django.test import TestCase

# from freezegun import freeze_time

# from ....dbs.memory.handler import MemoryDatabasePlugin
# from ..handler import FilesystemInputPlugin


# def test_filesystem_basic(tmpdir):
#     d = tmpdir.mkdir('data')
#     d.mkdir('subdata')

#     db = MemoryDatabasePlugin({})
#     fs = FilesystemInputPlugin({
#         'db': db,
#         'paths': [
#             {'path': str(d), 'virtual_root': ''}
#         ]
#     })

#     with freeze_time("2018-01-01"):
#         yield fs.rescan()

#     raise Exception(fs.list('', 10).serialize())


# class FilesystemInputHandlerTestCase(TestCase):
#     maxDiff = 5000
#     def setUp(self):
#         self.reactor = threaded_reactor()
#         self.temppath = tempfile.mkdtemp()

#         os.mkdir(os.path.join(self.temppath, 'data1'))
#         os.mkdir(os.path.join(self.temppath, 'data2'))
#         os.mkdir(os.path.join(self.temppath, 'data3'))
#         self.db_1 = MemoryDatabasePlugin({})
#         config = {
#             'db': self.db_1,
#             'paths': [
#                 {'path': os.path.join(self.temppath, 'data1'), 'virtual_root': 'data1'},
#                 {'path': os.path.join(self.temppath, 'data2'), 'virtual_root': 'data2'},
#             ]
#         }
#         self.fs_1 = FilesystemInputPlugin(config)

#         os.mkdir(os.path.join(self.temppath, 'data1', 'folder1'))
#         with open(os.path.join(self.temppath, 'data1', 'folder1', 'file1'), 'wb') as f:
#             f.write(b' ' * 20)

#         os.mkdir(os.path.join(self.temppath, 'data3', 'folder3'))
#         with open(os.path.join(self.temppath, 'data3', 'folder3', 'file3'), 'wb') as f:
#             f.write(b' ' * 30)

#         os.symlink(os.path.join(self.temppath, 'data3', 'folder3'), os.path.join(self.temppath, 'data1', 'folder3'))

#         os.mkdir(os.path.join(self.temppath, 'data1', 'folder2'))

#     def tearDown(self):
#         if self.temppath.startswith('/tmp'):
#             shutil.rmtree(self.temppath)

# @deferred()
# @defer.inlineCallbacks
# def test_rescan(self):
#     yield self.fs_1._rescan()

#     os.remove(os.path.join(self.temppath, 'data1', 'folder1', 'file1'))
#     os.rmdir(os.path.join(self.temppath, 'data1', 'folder1'))

#     yield self.fs_1._rescan()

#     listing = yield self.fs_1.list('', 3)
#     from pprint import pprint; pprint(listing.serialize())

#     raise Exception()
