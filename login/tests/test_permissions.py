from login.permissions import Permissions, get_permissions, cache_info, cache_clear
from login.tests.setup_data import TestSetup


class TestPermissions(TestSetup):

    def test(self):

        # superuser

        all_ambulances = {self.a1.id, self.a2.id, self.a3.id}
        all_hospitals = {self.h1.id, self.h2.id, self.h3.id}

        u = self.u1
        perms = Permissions(u)
        self.assertEqual(3, len(perms.ambulances))
        self.assertEqual(3, len(perms.hospitals))

        answer = [self.a1.id, self.a2.id, self.a3.id]
        self.assertCountEqual(answer, perms.get_can_read('ambulances'))
        for id in all_ambulances:
            if id in answer:
                self.assertTrue(perms.check_can_read(ambulance=id))
            else:
                self.assertFalse(perms.check_can_read(ambulance=id))
        self.assertCountEqual(answer, perms.get_can_write('ambulances'))
        for id in all_ambulances:
            if id in answer:
                self.assertTrue(perms.check_can_write(ambulance=id))
            else:
                self.assertFalse(perms.check_can_write(ambulance=id))

        answer = [self.h1.id, self.h2.id, self.h3.id]
        self.assertCountEqual(answer, perms.get_can_read('hospitals'))
        for id in all_hospitals:
            if id in answer:
                self.assertTrue(perms.check_can_read(hospital=id))
            else:
                self.assertFalse(perms.check_can_read(hospital=id))
        self.assertCountEqual(answer, perms.get_can_write('hospitals'))
        for id in all_hospitals:
            if id in answer:
                self.assertTrue(perms.check_can_write(hospital=id))
            else:
                self.assertFalse(perms.check_can_write(hospital=id))
        answer = {
            'ambulances': {
                self.a1.id: {
                    'ambulance': self.a1,
                    'can_read': True,
                    'can_write': True
                },
                self.a2.id: {
                    'ambulance': self.a2,
                    'can_read': True,
                    'can_write': True
                },
                self.a3.id: {
                    'ambulance': self.a3,
                    'can_read': True,
                    'can_write': True
                }
            },
            'hospitals': {
                self.h1.id: {
                    'hospital': self.h1,
                    'can_read': True,
                    'can_write': True
                },
                self.h2.id: {
                    'hospital': self.h2,
                    'can_read': True,
                    'can_write': True
                },
                self.h3.id: {
                    'hospital': self.h3,
                    'can_read': True,
                    'can_write': True
                }
            }
        }
        for id in all_ambulances:
            self.assertDictEqual(answer['ambulances'][id], perms.get(ambulance=id))
        for id in all_hospitals:
            self.assertDictEqual(answer['hospitals'][id], perms.get(hospital=id))

        # regular users without groups

        u = self.u2
        perms = Permissions(u)
        self.assertEqual(0, len(perms.ambulances))
        self.assertEqual(2, len(perms.hospitals))
        answer = []
        self.assertCountEqual(answer, perms.get_can_read('ambulances'))
        for id in all_ambulances:
            if id in answer:
                self.assertTrue(perms.check_can_read(ambulance=id))
            else:
                self.assertFalse(perms.check_can_read(ambulance=id))
        answer = []
        self.assertCountEqual(answer, perms.get_can_write('ambulances'))
        for id in all_ambulances:
            if id in answer:
                self.assertTrue(perms.check_can_write(ambulance=id))
            else:
                self.assertFalse(perms.check_can_write(ambulance=id))
        answer = [self.h1.id, self.h2.id]
        self.assertCountEqual(answer, perms.get_can_read('hospitals'))
        for id in all_hospitals:
            if id in answer:
                self.assertTrue(perms.check_can_read(hospital=id))
            else:
                self.assertFalse(perms.check_can_read(hospital=id))
        answer = [self.h2.id]
        self.assertCountEqual(answer, perms.get_can_write('hospitals'))
        for id in all_hospitals:
            if id in answer:
                self.assertTrue(perms.check_can_write(hospital=id))
            else:
                self.assertFalse(perms.check_can_write(hospital=id))
        answer = {
            'ambulances': {
            },
            'hospitals': {
                self.h1.id: {
                    'hospital': self.h1,
                    'can_read': True,
                    'can_write': False
                },
                self.h2.id: {
                    'hospital': self.h2,
                    'can_read': True,
                    'can_write': True
                },
            }
        }
        for id in all_ambulances:
            if id in answer['ambulances']:
                self.assertDictEqual(answer['ambulances'][id], perms.get(ambulance=id))
            else:
                with self.assertRaises(KeyError):
                    perms.get(ambulance=id)
        for id in all_hospitals:
            if id in answer['hospitals']:
                self.assertDictEqual(answer['hospitals'][id], perms.get(hospital=id))
            else:
                with self.assertRaises(KeyError):
                    perms.get(hospital=id)

        u = self.u3
        perms = Permissions(u)
        self.assertEqual(2, len(perms.ambulances))
        self.assertEqual(0, len(perms.hospitals))
        answer = [self.a3.id]
        self.assertCountEqual(answer, perms.get_can_read('ambulances'))
        for id in all_ambulances:
            if id in answer:
                self.assertTrue(perms.check_can_read(ambulance=id))
            else:
                self.assertFalse(perms.check_can_read(ambulance=id))
        answer = [self.a3.id]
        self.assertCountEqual(answer, perms.get_can_write('ambulances'))
        for id in all_ambulances:
            if id in answer:
                self.assertTrue(perms.check_can_write(ambulance=id))
            else:
                self.assertFalse(perms.check_can_write(ambulance=id))
        answer = []
        self.assertCountEqual(answer, perms.get_can_read('hospitals'))
        for id in all_hospitals:
            if id in answer:
                self.assertTrue(perms.check_can_read(hospital=id))
            else:
                self.assertFalse(perms.check_can_read(hospital=id))
        answer = []
        self.assertCountEqual(answer, perms.get_can_write('hospitals'))
        for id in all_hospitals:
            if id in answer:
                self.assertTrue(perms.check_can_write(hospital=id))
            else:
                self.assertFalse(perms.check_can_write(hospital=id))
        answer = {
            'ambulances': {
                self.a1.id: {
                    'ambulance': self.a1,
                    'can_read': False,
                    'can_write': False
                },
                self.a3.id: {
                    'ambulance': self.a3,
                    'can_read': True,
                    'can_write': True
                }
            },
            'hospitals': {
            }
        }
        for id in all_ambulances:
            if id in answer['ambulances']:
                self.assertDictEqual(answer['ambulances'][id], perms.get(ambulance=id))
            else:
                with self.assertRaises(KeyError):
                    perms.get(ambulance=id)
        for id in all_hospitals:
            if id in answer['hospitals']:
                self.assertDictEqual(answer['hospitals'][id], perms.get(hospital=id))
            else:
                with self.assertRaises(KeyError):
                    perms.get(hospital=id)

        # regular users with groups

        u = self.u4
        perms = Permissions(u)
        self.assertEqual(0, len(perms.ambulances))
        self.assertEqual(2, len(perms.hospitals))
        answer = []
        self.assertCountEqual(answer, perms.get_can_read('ambulances'))
        for id in all_ambulances:
            if id in answer:
                self.assertTrue(perms.check_can_read(ambulance=id))
            else:
                self.assertFalse(perms.check_can_read(ambulance=id))
        answer = []
        self.assertCountEqual(answer, perms.get_can_write('ambulances'))
        for id in all_ambulances:
            if id in answer:
                self.assertTrue(perms.check_can_write(ambulance=id))
            else:
                self.assertFalse(perms.check_can_write(ambulance=id))
        answer = [self.h1.id, self.h2.id]
        self.assertCountEqual(answer, perms.get_can_read('hospitals'))
        for id in all_hospitals:
            if id in answer:
                self.assertTrue(perms.check_can_read(hospital=id))
            else:
                self.assertFalse(perms.check_can_read(hospital=id))
        answer = [self.h2.id]
        self.assertCountEqual(answer, perms.get_can_write('hospitals'))
        for id in all_hospitals:
            if id in answer:
                self.assertTrue(perms.check_can_write(hospital=id))
            else:
                self.assertFalse(perms.check_can_write(hospital=id))
        answer = {
            'ambulances': {
            },
            'hospitals': {
                self.h1.id: {
                    'hospital': self.h1,
                    'can_read': True,
                    'can_write': False
                },
                self.h2.id: {
                    'hospital': self.h2,
                    'can_read': True,
                    'can_write': True
                },
            }
        }
        for id in all_ambulances:
            if id in answer['ambulances']:
                self.assertDictEqual(answer['ambulances'][id], perms.get(ambulance=id))
            else:
                with self.assertRaises(KeyError):
                    perms.get(ambulance=id)
        for id in all_hospitals:
            if id in answer['hospitals']:
                self.assertDictEqual(answer['hospitals'][id], perms.get(hospital=id))
            else:
                with self.assertRaises(KeyError):
                    perms.get(hospital=id)

        u = self.u5
        perms = Permissions(u)
        self.assertEqual(3, len(perms.ambulances))
        self.assertEqual(2, len(perms.hospitals))
        answer = [self.a2.id, self.a3.id]
        self.assertCountEqual(answer, perms.get_can_read('ambulances'))
        for id in all_ambulances:
            if id in answer:
                self.assertTrue(perms.check_can_read(ambulance=id))
            else:
                self.assertFalse(perms.check_can_read(ambulance=id))
        answer = [self.a2.id, self.a3.id]
        self.assertCountEqual(answer, perms.get_can_write('ambulances'))
        for id in all_ambulances:
            if id in answer:
                self.assertTrue(perms.check_can_write(ambulance=id))
            else:
                self.assertFalse(perms.check_can_write(ambulance=id))
        answer = [self.h1.id, self.h3.id]
        self.assertCountEqual(answer, perms.get_can_read('hospitals'))
        for id in all_hospitals:
            if id in answer:
                self.assertTrue(perms.check_can_read(hospital=id))
            else:
                self.assertFalse(perms.check_can_read(hospital=id))
        answer = [self.h1.id]
        self.assertCountEqual(answer, perms.get_can_write('hospitals'))
        for id in all_hospitals:
            if id in answer:
                self.assertTrue(perms.check_can_write(hospital=id))
            else:
                self.assertFalse(perms.check_can_write(hospital=id))
        answer = {
            'ambulances': {
                self.a1.id: {
                    'ambulance': self.a1,
                    'can_read': False,
                    'can_write': False
                },
                self.a2.id: {
                    'ambulance': self.a2,
                    'can_read': True,
                    'can_write': True
                },
                self.a3.id: {
                    'ambulance': self.a3,
                    'can_read': True,
                    'can_write': True
                }
            },
            'hospitals': {
                self.h1.id: {
                    'hospital': self.h1,
                    'can_read': True,
                    'can_write': True
                },
                self.h3.id: {
                    'hospital': self.h3,
                    'can_read': True,
                    'can_write': False
                }
            }
        }
        for id in all_ambulances:
            if id in answer['ambulances']:
                self.assertDictEqual(answer['ambulances'][id], perms.get(ambulance=id))
            else:
                with self.assertRaises(KeyError):
                    perms.get(ambulance=id)
        for id in all_hospitals:
            if id in answer['hospitals']:
                self.assertDictEqual(answer['hospitals'][id], perms.get(hospital=id))
            else:
                with self.assertRaises(KeyError):
                    perms.get(hospital=id)

        # Group priority testing
        u = self.u6
        perms = Permissions(u)
        self.assertEqual(1, len(perms.ambulances))
        self.assertEqual(0, len(perms.hospitals))
        answer = []
        self.assertCountEqual(answer, perms.get_can_read('ambulances'))
        self.assertCountEqual(answer, perms.get_can_write('ambulances'))
        answer = {
            'ambulances': {
                self.a1.id: {
                    'ambulance': self.a1,
                    'can_read': False,
                    'can_write': False
                },
            },
            'hospitals': {}
        }
        for id in all_ambulances:
            if id in answer['ambulances']:
                self.assertDictEqual(answer['ambulances'][id], perms.get(ambulance=id))
            else:
                with self.assertRaises(KeyError):
                    perms.get(ambulance=id)
        for id in all_hospitals:
            if id in answer['hospitals']:
                self.assertDictEqual(answer['hospitals'][id], perms.get(hospital=id))
            else:
                with self.assertRaises(KeyError):
                    perms.get(hospital=id)

        u = self.u7
        perms = Permissions(u)
        self.assertEqual(1, len(perms.ambulances))
        self.assertEqual(0, len(perms.hospitals))
        answer = [self.a1.id]
        self.assertCountEqual(answer, perms.get_can_read('ambulances'))
        self.assertCountEqual(answer, perms.get_can_write('ambulances'))
        answer = {
            'ambulances': {
                self.a1.id: {
                    'ambulance': self.a1,
                    'can_read': True,
                    'can_write': True
                },
            },
            'hospitals': {}
        }
        for id in all_ambulances:
            if id in answer['ambulances']:
                self.assertDictEqual(answer['ambulances'][id], perms.get(ambulance=id))
            else:
                with self.assertRaises(KeyError):
                    perms.get(ambulance=id)
        for id in all_hospitals:
            if id in answer['hospitals']:
                self.assertDictEqual(answer['hospitals'][id], perms.get(hospital=id))
            else:
                with self.assertRaises(KeyError):
                    perms.get(hospital=id)          

    def test_cache(self):

        # clear cache
        cache_clear()

        # retrieve permissions for user u1
        get_permissions(self.u1)
        get_permissions(self.u1)
        get_permissions(self.u1)
        get_permissions(self.u1)
        info = cache_info()
        self.assertEqual(info.hits, 3)
        self.assertEqual(info.misses, 1)
        self.assertEqual(info.currsize, 1)

        # retrieve permissions for user u2 and u1
        get_permissions(self.u2)
        get_permissions(self.u1)
        get_permissions(self.u2)
        get_permissions(self.u1)
        info = cache_info()
        self.assertEqual(info.hits, 6)
        self.assertEqual(info.misses, 2)
        self.assertEqual(info.currsize, 2)
