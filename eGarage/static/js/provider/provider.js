/* E-GARAGE — provider.js */

var sidebar      = document.getElementById('sidebar');
var sbOverlay    = document.getElementById('sbOverlay');
var sbClose      = document.getElementById('sbClose');
var hamburgerBtn = document.getElementById('hamburgerBtn');

/* ── DEBUG: log what we found ── */
console.log('sidebar:', sidebar);
console.log('sbOverlay:', sbOverlay);
console.log('sbClose:', sbClose);
console.log('hamburgerBtn:', hamburgerBtn);

function openSidebar() {
  console.log('openSidebar called');
  if (!sidebar) return;
  sidebar.classList.add('open');
  if (sbOverlay) sbOverlay.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeSidebar() {
  console.log('closeSidebar called');
  if (!sidebar) return;
  sidebar.classList.remove('open');
  if (sbOverlay) sbOverlay.classList.remove('open');
  document.body.style.overflow = '';
}

window.openSidebar  = openSidebar;
window.closeSidebar = closeSidebar;

if (hamburgerBtn) {
  hamburgerBtn.addEventListener('click', function (e) {
    e.preventDefault();
    e.stopPropagation();
    console.log('hamburger clicked, sidebar open:', sidebar && sidebar.classList.contains('open'));
    if (sidebar && sidebar.classList.contains('open')) {
      closeSidebar();
    } else {
      openSidebar();
    }
  });
} else {
  console.error('hamburgerBtn NOT FOUND — check id="hamburgerBtn" exists in HTML');
}

if (sbClose)   sbClose.addEventListener('click',   function(e){ e.stopPropagation(); closeSidebar(); });
if (sbOverlay) sbOverlay.addEventListener('click',  closeSidebar);

document.addEventListener('keydown', function(e){ if(e.key==='Escape') closeSidebar(); });

var mainContent = document.querySelector('.main-content');
if (mainContent) {
  mainContent.addEventListener('click', function(){
    if (sidebar && sidebar.classList.contains('open')) closeSidebar();
  });
}

/* Swipe */
var _sx=0,_sy=0;
document.addEventListener('touchstart',function(e){_sx=e.touches[0].clientX;_sy=e.touches[0].clientY;},{passive:true});
document.addEventListener('touchend',function(e){
  var dx=e.changedTouches[0].clientX-_sx, dy=e.changedTouches[0].clientY-_sy;
  if(Math.abs(dy)>Math.abs(dx)) return;
  if(dx>60&&_sx<=30) openSidebar();
  if(dx<-60&&sidebar&&sidebar.classList.contains('open')) closeSidebar();
},{passive:true});

/* Resize */
window.addEventListener('resize',function(){
  if(window.innerWidth>900){closeSidebar();document.body.style.overflow='';}
});

/* Topnav shadow */
var topnav=document.querySelector('.topnav');
if(topnav){
  window.addEventListener('scroll',function(){
    topnav.style.boxShadow=window.scrollY>4?'0 4px 18px rgba(30,58,95,0.11)':'0 2px 8px rgba(30,58,95,0.07)';
  },{passive:true});
}

/* Alert dismiss */
document.querySelectorAll('.alert').forEach(function(a){
  var b=document.createElement('button');
  b.innerHTML='<i class="fas fa-times"></i>';
  b.style.cssText='margin-left:auto;background:none;border:none;cursor:pointer;opacity:0.6;padding:0 0 0 12px;font-size:0.85rem';
  b.onclick=function(){
    a.style.transition='opacity 0.4s';a.style.opacity='0';
    setTimeout(function(){if(a.parentNode)a.parentNode.removeChild(a);},400);
  };
  a.style.display='flex';a.style.alignItems='center';
  a.appendChild(b);
  setTimeout(function(){b.click();},5000);
});

/* Notif dot pulse */
var dot=document.querySelector('.notif-dot');
if(dot){var _on=true;setInterval(function(){_on=!_on;dot.style.opacity=_on?'1':'0.3';},1400);}

/* Back to top */
var btt=document.createElement('button');
btt.innerHTML='<i class="fas fa-chevron-up"></i>';
btt.style.cssText='position:fixed;bottom:28px;right:28px;width:40px;height:40px;border-radius:50%;background:#e8560a;color:#fff;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 14px rgba(232,86,10,0.35);opacity:0;transition:opacity 0.3s;z-index:300';
document.body.appendChild(btt);
window.addEventListener('scroll',function(){btt.style.opacity=window.scrollY>300?'1':'0';},{passive:true});
btt.onclick=function(){window.scrollTo({top:0,behavior:'smooth'});};

/* Confirm delete */
document.querySelectorAll('form[data-confirm]').forEach(function(f){
  f.addEventListener('submit',function(e){if(!confirm(f.getAttribute('data-confirm')||'Are you sure?'))e.preventDefault();});
});

/* Modal overlay close */
document.querySelectorAll('.modal-overlay').forEach(function(o){
  o.addEventListener('click',function(e){if(e.target===o)o.classList.remove('open');});
});

/* Invoice recalc */
var _bp=window.INVOICE_BASE_PRICE||0;
function _recalc(){
  var g=document.getElementById('gstInput');if(!g)return;
  var d=document.getElementById('discInput');
  var gp=parseFloat(g.value)||0,dc=parseFloat(d?d.value:0)||0;
  var gst=Math.round(_bp*gp/100),tot=Math.max(0,_bp+gst-dc);
  var fmt=function(n){return '₹'+n.toLocaleString('en-IN');};
  [['dispGstPct',gp],['dispGstAmt',fmt(gst)],['dispDiscAmt','− '+fmt(dc)],
   ['dispTotal',fmt(tot)],['summGst',fmt(gst)],['summDisc',fmt(dc)],['summTotal',fmt(tot)]
  ].forEach(function(p){var e=document.getElementById(p[0]);if(e)e.textContent=p[1];});
  var gh=document.getElementById('gstAmtHidden');if(gh)gh.value=gst;
  var th=document.getElementById('totalHidden');if(th)th.value=tot;
  var dr=document.getElementById('discRow');if(dr)dr.style.display=dc>0?'':'none';
}
['gstInput','discInput'].forEach(function(id){var e=document.getElementById(id);if(e)e.addEventListener('input',_recalc);});
if(document.getElementById('gstInput'))_recalc();

/* ── GLOBAL UTILITY FUNCTIONS ── */
function showToast(msg,type){
  type=type||'success';
  var t=document.getElementById('toast');
  if(!t){
    t=document.createElement('div');t.id='toast';
    t.style.cssText='position:fixed;bottom:24px;right:24px;z-index:99999;background:#1a2332;color:#fff;padding:12px 18px;border-radius:10px;font-size:0.85rem;font-weight:600;display:flex;align-items:center;gap:10px;box-shadow:0 8px 28px rgba(0,0,0,0.22);transition:opacity 0.3s,transform 0.3s;opacity:0;transform:translateY(10px);min-width:220px';
    t.innerHTML='<i id="toastIcon" class="fas fa-check-circle"></i><span id="toastMsg"></span>';
    document.body.appendChild(t);
  }
  var icons={success:'fa-check-circle',danger:'fa-times-circle',warning:'fa-exclamation-circle'};
  var colors={success:'#16a34a',danger:'#dc2626',warning:'#f59e0b'};
  var ic=document.getElementById('toastIcon');if(ic)ic.className='fas '+(icons[type]||icons.success);
  var ms=document.getElementById('toastMsg');if(ms)ms.textContent=msg;
  t.style.borderLeft='4px solid '+(colors[type]||colors.success);
  t.style.opacity='1';t.style.transform='translateY(0)';
  clearTimeout(t._tmr);
  t._tmr=setTimeout(function(){t.style.opacity='0';t.style.transform='translateY(10px)';},3500);
}

function openModal(id){var e=document.getElementById(id);if(e)e.classList.add('open');}
function closeModal(id){var e=document.getElementById(id);if(e)e.classList.remove('open');}

function getCookie(n){
  var v='; '+document.cookie,p=v.split('; '+n+'=');
  if(p.length===2)return p.pop().split(';').shift();return '';
}

function markNotifRead(nId,url){
  fetch(url,{method:'POST',headers:{'X-CSRFToken':getCookie('csrftoken')}})
  .then(function(){
    var i=document.querySelector('[data-notif-id="'+nId+'"]');
    if(i){i.classList.remove('unread');i.classList.add('read');}
    var b=document.getElementById('notifBadge');
    if(b){var c=(parseInt(b.textContent)||1)-1;b.textContent=c;if(c<=0)b.style.display='none';}
  });
}

function markAllNotifsRead(url){
  fetch(url,{method:'POST',headers:{'X-CSRFToken':getCookie('csrftoken')}})
  .then(function(){
    document.querySelectorAll('.notif-item.unread').forEach(function(n){n.classList.remove('unread');n.classList.add('read');});
    var b=document.getElementById('notifBadge');if(b)b.style.display='none';
    showToast('All notifications marked as read','success');
  });
}

console.info('[E-Garage Provider] JS ready.');