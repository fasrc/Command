"""
Created on Oct 9, 2014
Copyright (c) 2014
Harvard FAS Research Computing
All rights reserved.

@author: Aaron Kitzmiller
"""
import subprocess,os,socket
import datetime,time
from command import ShellRunner,RunLog,RunHandler,Command,DefaultFileLogger
from command.slurm import SbatchCommand
from command.slurm.sbatch import SBATCH_NOSUBMIT_OPTIONS

class SlurmRunner(ShellRunner):
    """
    ShellRunner class that gets job ids instead of pids and uses squeue
    to determine status
    """
    def __init__(self,logger=DefaultFileLogger(),verbose=0,usevenv=False):
        super(self.__class__,self).__init__(logger=logger,verbose=verbose,usevenv=usevenv)

    def getSlurmStatus(self,jobid):
        checkcmd = "squeue -j %s --format=%%T -h" % jobid
        if self.verbose > 1: 
            print "checkcmd %s" % checkcmd
        p = subprocess.Popen(checkcmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        (out,err) = p.communicate()
        out = out.strip()
        err = err.strip()
        if self.verbose > 1:
            print "squeue out %s err %s" % (out,err)
        if out is not None and out != "":
            # It's still running
            return out
        else:
            # Get the result from sacct
            sacctcmd = "sacct -j %s.batch --format=State -n" % jobid
            p = subprocess.Popen(sacctcmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            (out,err) = p.communicate()
            out = out.strip()
            err = err.strip()
            if self.verbose > 1:
                print "sacct out is %s" % out
            return out
        
    def checkStatus(self,runlog=None,proc=None):
        """
        Checks the status of processes using squeue.
        Runlog must have a job id in it 
        """
        if runlog is None:
            raise Exception("Cannot checkStatus without runlog")
        
        # If it's a "help" or "usage" run, just use the parent checkStatus
        for option in SBATCH_NOSUBMIT_OPTIONS:
            if "--%s" % option in runlog["cmdstring"]:
                return super(self.__class__,self).checkStatus(runlog,proc)
       
        result = self.getSlurmStatus(runlog["jobid"]) 
        if result in ["CANCELLED","COMPLETED","FAILED","TIMEOUT","NODE_FAIL","SPECIAL_EXIT"]:
            return result
        else:
            return None
                 
        
    def run(self,cmd,runhandler=None,runsetname=None,stdoutfile=None,stderrfile=None,logger=None):
        """
        Runs a Command and returns a RunHandler.
        If output and error options are set on the SbatchCommand, they will be set as those values
        in the yaml file.
        """
        if logger is None:
            logger = self.logger
        if runsetname is None:
            runsetname = logger.getRunsetName()
        if runhandler is None:
            runhandler = RunHandler(logger,runsetname)
        if isinstance(cmd,basestring):
            cmd = Command(cmd)
        if isinstance(cmd,SbatchCommand):
            if cmd.output:
                stdoutfile = cmd.output
            if cmd.error:
                stderrfile = cmd.error
        runhandler.setCmd(cmd,runner=self,stdoutfile=stdoutfile,stderrfile=stderrfile)
        runhandler.doRun()
        return runhandler
             
    def execute(self,cmd,runsetname,stdoutfile=None,stderrfile=None,logger=None):
        """
        Method that actually executes the Command(s).
        """
        # For options like "help" and "usage", the parent method should be called.
        for option in SBATCH_NOSUBMIT_OPTIONS:
            if "--%s" % option in cmd:
                return super(self.__class__,self).execute(cmd,runsetname,stdoutfile=stdoutfile,stderrfile=stderrfile,logger=logger)
                
        if logger is None:
            logger = self.logger
        if stdoutfile is None:
            stdoutfile = logger.getStdOutFileName()
        if stderrfile is None:
            stderrfile = logger.getStdErrFileName()
             
         
        hostname = socket.gethostname().split('.',1)[0]
        pid = os.fork()
        if pid == 0:
            proc = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            (out,err) = proc.communicate()
            if err:
                raise Exception("sbatch submission failed %s" % err)
            
            jobid = out.split()[-1]
            
            starttime = datetime.datetime.now()
            runset = []
            runlog = RunLog( jobid=jobid,
                             cmdstring=cmd,
                             starttime=starttime,
                             hostname=hostname,
                             stdoutfile=stdoutfile,
                             stderrfile=stderrfile,
                             runner="%s.%s" % (self.__module__, self.__class__.__name__)
            )
            runset.append(runlog)
            if self.verbose > 0:
                print runlog
            logger.saveRunSet(runset, runsetname)
            os._exit(0)
        else:
            # Wait until the runset file has been written
            ready = False
            while not ready:
                time.sleep(2)
                try:
                    logger.getRunSet(runsetname)
                    ready = True
                except Exception:
                    pass
        return None
    

