// Shared request lifecycle and accessible feedback for the dashboard and sign-in.
const messages={
 400:'Review the submitted fields and try again.',
 401:'Your session expired. Sign in with Google again.',
 403:'This session cannot perform that action. Sign in with the approved Google account.',
 409:'This record changed elsewhere. Refresh and reopen it before saving.',
 429:'Too many requests. Wait a moment before trying again.'
};
export async function requestJSON(url,options={}){
 const controller=new AbortController();
 const signal=options.signal?AbortSignal.any([options.signal,controller.signal]):controller.signal;
 const timer=setTimeout(()=>controller.abort(),25000);
 const method=options.method||'GET';
 try{
  const response=await fetch(url,{...options,signal});
  const data=await response.json().catch(()=>null);
  if(!response.ok){
   const detail=response.status===400&&typeof data?.error==='string'?data.error:null;
   throw Object.assign(new Error(detail||messages[response.status]||'The service is temporarily unavailable. Try again shortly.'),{status:response.status});
  }
  if(!data)throw new Error('The service returned an unreadable response. Refresh and try again.');
  return data;
 }catch(error){
  if(error.status===401&&typeof location!=='undefined'&&location.hostname!=='127.0.0.1')location.replace('/login?status=expired');
  if(controller.signal.aborted)throw new Error(method==='GET'?'The request timed out. Try again.':'Confirmation timed out. Refresh records before submitting again.');
  if(options.signal?.aborted)throw new DOMException('Operation cancelled.','AbortError');
  if(error instanceof TypeError)throw new Error(method==='GET'?'Unable to connect. Check your connection and retry.':'Connection lost before confirmation. Refresh records before submitting again.');
  throw error;
 }finally{clearTimeout(timer);}
}
const timers=new WeakMap();
export function feedback(element,state,message='',retry){
 clearTimeout(timers.get(element));
 element.dataset.feedback=state;
 element.textContent=message;
 element.setAttribute('aria-live',state==='failed'?'assertive':'polite');
 if(retry){
  const button=document.createElement('button');
  button.type='button';
  button.textContent='Retry';
  button.onclick=()=>{
   feedback(element,'retrying','Retrying…');
   retry();
  };
  element.append(' ',button);
 }
 if(element.id==='toast'){
  element.classList.toggle('show',state!=='idle');
  if(['success','cancelled','warning'].includes(state))timers.set(element,setTimeout(()=>element.classList.remove('show'),4500));
 }
}
export function busy(button,label){
 const previous=button.textContent;
 button.disabled=true;
 button.setAttribute('aria-busy','true');
 button.textContent=label;
 return ()=>{
  button.disabled=false;
  button.removeAttribute('aria-busy');
  button.textContent=previous;
 };
}
