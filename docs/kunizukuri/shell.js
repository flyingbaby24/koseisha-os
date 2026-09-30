const header=document.querySelector('.site-header');
const nav=document.querySelector('.site-nav');
const toggle=document.querySelector('.nav-toggle');
toggle?.addEventListener('click',()=>{const open=nav.classList.toggle('open');toggle.setAttribute('aria-expanded',String(open));});
nav?.querySelectorAll('a').forEach(link=>link.addEventListener('click',()=>{nav.classList.remove('open');toggle?.setAttribute('aria-expanded','false');}));
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&nav?.classList.contains('open')){nav.classList.remove('open');toggle?.setAttribute('aria-expanded','false');toggle?.focus();}});
const updateHeader=()=>header?.classList.toggle('scrolled',window.scrollY>24);
updateHeader();window.addEventListener('scroll',updateHeader,{passive:true});
