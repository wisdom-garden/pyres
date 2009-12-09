from tests import PyResTests, Basic, TestProcess, ErrorObject
from pyres import ResQ
from pyres.job import Job
from pyres.worker import Worker
import os
class WorkerTests(PyResTests):
    def test_worker_init(self):
        from pyres.exceptions import NoQueueError
        self.assertRaises(NoQueueError, Worker,[])
        self.assertRaises(Exception, Worker,['test'],TestProcess())
    
    def test_startup(self):
        worker = Worker(['basic'])
        worker.startup()
        name = "%s:%s:%s" % (os.uname()[1],os.getpid(),'basic')
        assert self.redis.sismember('workers',name)
        import signal
        assert signal.getsignal(signal.SIGTERM) == worker.shutdown_all
        assert signal.getsignal(signal.SIGINT) == worker.shutdown_all
        assert signal.getsignal(signal.SIGQUIT) == worker.schedule_shutdown
        assert signal.getsignal(signal.SIGUSR1) == worker.kill_child
    
    def test_register(self):
        worker = Worker(['basic'])
        worker.register_worker()
        name = "%s:%s:%s" % (os.uname()[1],os.getpid(),'basic')
        assert self.redis.sismember('workers',name)
    
    def test_unregister(self):
        worker = Worker(['basic'])
        worker.register_worker()
        name = "%s:%s:%s" % (os.uname()[1],os.getpid(),'basic')
        assert self.redis.sismember('workers',name)
        worker.unregister_worker()
        assert name not in self.redis.smembers('workers')
    
    def test_working_on(self):
        name = "%s:%s:%s" % (os.uname()[1],os.getpid(),'basic')
        self.resq.enqueue(Basic,"test1")
        job = Job.reserve('basic', self.resq)
        worker = Worker(['basic'])
        worker.working_on(job)
        assert self.redis.exists("worker:%s" % name)
    
    def test_processed(self):
        name = "%s:%s:%s" % (os.uname()[1],os.getpid(),'basic')
        worker = Worker(['basic'])
        worker.processed()
        assert self.redis.exists("stat:processed")
        assert self.redis.exists("stat:processed:%s" % name)
        assert self.redis.get("stat:processed") == 1
        assert self.redis.get("stat:processed:%s" % name) == 1
        worker.processed()
        assert self.redis.get("stat:processed") == 2
        assert self.redis.get("stat:processed:%s" % name) == 2
    
    def test_failed(self):
        name = "%s:%s:%s" % (os.uname()[1],os.getpid(),'basic')
        worker = Worker(['basic'])
        worker.failed()
        assert self.redis.exists("stat:failed")
        assert self.redis.exists("stat:failed:%s" % name)
        assert self.redis.get("stat:failed") == 1
        assert self.redis.get("stat:failed:%s" % name) == 1
        worker.failed()
        assert self.redis.get("stat:failed") == 2
        assert self.redis.get("stat:failed:%s" % name) == 2
    
    def test_process(self):
        name = "%s:%s:%s" % (os.uname()[1],os.getpid(),'basic')
        self.resq.enqueue(Basic,"test1")
        job = Job.reserve('basic', self.resq)
        worker = Worker(['basic'])
        worker.process(job)
        assert not self.redis.get('worker:%s' % worker)
        assert not self.redis.get("stat:failed")
        assert not self.redis.get("stat:failed:%s" % name)
        self.resq.enqueue(Basic,"test1")
        worker.process()
        assert not self.redis.get('worker:%s' % worker)
        assert not self.redis.get("stat:failed")
        assert not self.redis.get("stat:failed:%s" % name)
        
    
    def test_signals(self):
        worker = Worker(['basic'])
        worker.startup()
        import inspect, signal
        frame = inspect.currentframe()
        worker.schedule_shutdown(frame, signal.SIGQUIT)
        assert worker._shutdown
        del worker
        worker = Worker(['high'])
        #self.resq.enqueue(TestSleep)
        #worker.work()
        #assert worker.child
        assert not worker.kill_child(frame, signal.SIGUSR1)
    
    def test_job_failure(self):
        self.resq.enqueue(ErrorObject)
        worker = Worker(['basic'])
        worker.process()
        name = "%s:%s:%s" % (os.uname()[1],os.getpid(),'basic')
        assert not self.redis.get('worker:%s' % worker)
        assert self.redis.get("stat:failed") == 1
        assert self.redis.get("stat:failed:%s" % name) == 1
    
    def test_get_job(self):
        worker = Worker(['basic'])
        self.resq.enqueue(Basic,"test1")
        job = Job.reserve('basic', self.resq)
        worker.working_on(job)
        name = "%s:%s:%s" % (os.uname()[1],os.getpid(),'basic')
        assert worker.job() == ResQ.decode(self.redis.get('worker:%s' % name))
        worker.done_working()
        w2 = Worker(['basic'])
        print w2.job()
        assert w2.job() == {}
    
    def test_working(self):
        worker = Worker(['basic'])
        self.resq.enqueue_from_string('tests.Basic','basic','test1')
        worker.register_worker()
        job = Job.reserve('basic', self.resq)
        worker.working_on(job)
        name = "%s:%s:%s" % (os.uname()[1],os.getpid(),'basic')
        workers = Worker.working(self.resq)
        assert len(workers) == 1
        assert str(worker) == str(workers[0])
        assert worker != workers[0]
    
    def test_started(self):
        import datetime
        worker = Worker(['basic'])
        dt = datetime.datetime.now()
        worker.started = dt
        name = "%s:%s:%s" % (os.uname()[1],os.getpid(),'basic')
        assert self.redis.get('worker:%s:started' % name) == dt.strftime('%Y-%m-%d %H:%M:%S')
        assert worker.started == datetime.datetime.strptime(dt.strftime('%Y-%m-%d %H:%M:%S'),'%Y-%m-%d %H:%M:%S')
        worker.started = None
        assert not self.redis.exists('worker:%s:started' % name)