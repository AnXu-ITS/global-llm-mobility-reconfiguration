"""Thread-safe response mailbox; simulated arrival times are explicit test input.

Not a Codex process launcher. Workers may enqueue immutable proposals, while
only the world's owner can admit/apply them. Zero-delay responses wait one tick.
"""
from dataclasses import dataclass
from queue import SimpleQueue
from .core import Proposal

@dataclass(frozen=True)
class Request:
    request_id:str
    proposal:Proposal
    issued_at:int

@dataclass(frozen=True)
class Response:
    request_id:str
    proposal:Proposal
    ready_at:int

class ResponseMailbox:
    def __init__(self,kernel):
        self.kernel=kernel;self.requests={};self.cancelled=set();self.received=set()
        self.queue=SimpleQueue();self.deferred=[]
    def issue(self,request_id,proposal):
        self.kernel._owner()
        if request_id in self.requests:raise ValueError('request id already used')
        if any(r.proposal.mission_id==proposal.mission_id and key not in self.received|self.cancelled for key,r in self.requests.items()):
            raise ValueError('one in-flight request per mission')
        request=Request(request_id,proposal,self.kernel.now);self.requests[request_id]=request
        self.kernel.emit('REQUEST_ISSUED',request=request_id,operation=proposal.operation_id)
        return request
    def enqueue(self,response):
        if not isinstance(response,Response):raise TypeError('immutable Response required')
        self.queue.put(response)
    def cancel(self,request_id):
        self.kernel._owner();self.cancelled.add(request_id)
        self.kernel.emit('REQUEST_CANCELLED',request=request_id)
    def drain(self):
        self.kernel._owner()
        while not self.queue.empty():self.deferred.append(self.queue.get())
        waiting=[];accepted=[]
        for response in self.deferred:
            request=self.requests.get(response.request_id)
            if request is None or response.proposal!=request.proposal:
                self.kernel.emit('RESPONSE_BINDING_REJECTED',request=response.request_id);continue
            if self.kernel.now<max(request.issued_at+1,response.ready_at):waiting.append(response);continue
            if response.request_id in self.cancelled:
                self.kernel.emit('CANCELLED_RESPONSE_DISCARDED',request=response.request_id);continue
            if response.request_id in self.received:
                self.kernel.emit('DUPLICATE_RESPONSE_DISCARDED',request=response.request_id);continue
            self.received.add(response.request_id)
            if self.kernel.admit(response.proposal):accepted.append(response.proposal.operation_id)
        self.deferred=waiting
        return accepted
