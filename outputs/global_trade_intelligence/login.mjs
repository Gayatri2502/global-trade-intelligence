import {feedback} from './feedback.mjs';
const link=document.querySelector('.login-button');
const status=document.querySelector('#login-status');
const messages={
 expired:'Your session expired. Sign in again to continue.',
 denied:'This Google account has no access. Choose the approved account.',
 failed:'Google sign-in could not be verified. Start a new sign-in.',
 cancelled:'Sign-in was cancelled. You can try again.'
};
const message=messages[new URLSearchParams(location.search).get('status')];
if(message)feedback(status,'warning',message);
let timer;
function reset(){
 clearTimeout(timer);
 link.removeAttribute('aria-disabled');
}
window.addEventListener('pageshow',reset);
link.addEventListener('click',event=>{
 if(link.hasAttribute('aria-disabled')){event.preventDefault();return;}
 link.setAttribute('aria-disabled','true');
 feedback(status,'loading','Opening Google sign-in…');
 timer=setTimeout(()=>{reset();feedback(status,'warning','Google has not opened yet. Try signing in again.');},12000);
});
