import time


t1 = time.strptime('2018-04-18 10:00:00', '%Y-%m-%d %H:%M:%S')
t2 = time.mktime(t1)
print 't1=%s' %t1
print 't2=%s' %t2
t3 = time.time()
print 't3=%s' %t3

# n_time = time.time()
# e_time = time.mktime(n_time.timetuple())
# print e_time