"""
Created on Oct 9, 2014
Copyright (c) 2014
Harvard FAS Research Computing
All rights reserved.

@author: Aaron Kitzmiller
"""
import subprocess,os,socket
import datetime,time
from cmd import ShellRunner,RunLog,RunHandler,Command
from cmd.slurm import SbatchCommand

class SlurmRunner(ShellRunner):
    """
    ShellRunner class that gets job ids instead of pids and uses squeue
    to determine status
    """
    def checkStatus(self,runlog=None,proc=None):
        """
        Checks the status of processes using squeue.
        Runlog must have a job id in it 
        """
        checkcmd = "squeue -j %d --format='\%A' -h" % runlog['jobid']
        p = subprocess.call(checkcmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        (out,err) = p.communicate()
        if out is not None:
            # It's still running
            return None
        else:
            # Get the result from sacct
            sacctcmd = "sacct -j %d.batch --format=State -n" % runlog['jobid']
            p = subprocess.call(sacctcmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            (out,err) = p.communicate()
            return out.strip()
        
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
        return runhandler
             
    def execute(self,cmd,runsetname,stdoutfile=None,stderrfile=None,logger=None):
        """
        Method that actually executes the Command(s).
        """
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
        #print "Path is %s Runset name is %s" % (logger.pathname, runsetname)
            logger.saveRunSet(runset, runsetname)
            os._exit(0)
        else:
            time.sleep(1)
        return None
    