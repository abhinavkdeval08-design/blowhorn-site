// Signal home section reveals (layouts/_partials/home/signal.html).
// Each section.section below the hero settles in once as it scrolls into
// view: opacity and a 20px rise, about 0.65s. The eyebrow, headline and
// lede stagger by 0.08s and land a beat before the body. Motion's
// animate, inView and stagger only (layouts/home.html builds this file
// with js.Build). Readers who ask for less motion, or without the script,
// see every section as drawn. The hidden start is set here, never in CSS.
// Nothing already on screen is hidden. A hash jump or focus inside a
// hidden section shows it at once, with no animation. .iface-art is left
// to ai-cards.js.
import { animate } from 'motion/mini';
import { inView, stagger } from 'motion';

const main = document.querySelector('main.home-signal');
const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
if (main && !reduce && 'IntersectionObserver' in window) {
  const ease = [0.2, 0.7, 0.2, 1];
  const duration = 0.65;
  const shift = 'translateY(20px)';
  const rest = 'translateY(0px)';
  const step = 0.08;
  const jobs = new Map();

  function sectionOf(node) {
    let el = node && node.nodeType === 1 ? node : null;
    while (el && el !== main) {
      if (el.tagName === 'SECTION' && el.classList.contains('section') && el.parentElement === main) return el;
      el = el.parentElement;
    }
    return null;
  }

  function hashSection() {
    const hash = location.hash;
    if (hash.length < 2) return null;
    let id = hash.slice(1);
    try { id = decodeURIComponent(id); } catch (err) { /* keep the raw id */ }
    const el = document.getElementById(id);
    return el ? sectionOf(el) : null;
  }

  // Already on screen at run time: leave it painted. Hiding it would flash
  // and can hurt LCP. Transform and opacity never change layout.
  function onScreen(el) {
    const box = el.getBoundingClientRect();
    return box.bottom > 0 && box.top < window.innerHeight;
  }

  function keep(el) {
    return !el.matches('.iface-art');
  }

  // Headline bits stagger on their own. Everything else in the section
  // (each .section-body and the other blocks beside the head) follows
  // one beat later. Ancestors of the head stay put, so a parent opacity
  // cannot flatten that stagger.
  function pieces(section) {
    const head = section.querySelector('.section-head');
    if (!head) {
      const root = section.querySelector(':scope > .wrap') || section;
      return { head: [], rest: [...root.children].filter(keep) };
    }
    const headBits = [...head.children].filter(keep);
    const rest = [];
    let node = head;
    while (node && node !== section) {
      const parent = node.parentElement;
      if (!parent) break;
      [...parent.children].forEach((child) => {
        if (child !== node && keep(child)) rest.push(child);
      });
      node = parent;
    }
    return { head: headBits, rest };
  }

  function clear(els) {
    els.forEach((el) => {
      el.style.removeProperty('opacity');
      el.style.removeProperty('transform');
    });
  }

  function stop(job) {
    if (!job.stop) return;
    try { job.stop(); } catch (err) { /* already finished */ }
  }

  // Motion writes the end keyframes inline, including translateY(0). That
  // still boxes descendants (hover, view timelines, the other home
  // scripts), so drop both properties once the motion is done.
  function finish(job, token) {
    if (job.token !== token) return;
    job.token = null;
    job.done = true;
    stop(job);
    clear(job.targets);
  }

  function showNow(section) {
    const job = jobs.get(section);
    if (!job || job.done) return;
    job.token = null;
    job.done = true;
    stop(job);
    clear(job.targets);
  }

  function play(section) {
    const job = jobs.get(section);
    if (!job || job.done || job.played) return;
    job.played = true;
    const token = {};
    job.token = token;
    const to = { opacity: 1, transform: rest };
    const anims = [];
    if (job.head.length) {
      anims.push(animate(job.head, to, { duration, delay: stagger(step), ease }));
    }
    if (job.rest.length) {
      anims.push(animate(job.rest, to, { duration, delay: job.head.length * step, ease }));
    }
    job.stop = () => anims.forEach((anim) => anim.stop());
    const end = duration + job.head.length * step;
    window.setTimeout(() => finish(job, token), (end + 0.05) * 1000);
    Promise.all(anims.map((anim) => anim.then(() => {}, () => {}))).then(() => finish(job, token));
  }

  const jumped = hashSection();
  const focused = sectionOf(document.activeElement);

  main.querySelectorAll(':scope > section.section').forEach((section) => {
    if (section === jumped || section === focused || onScreen(section)) return;
    const part = pieces(section);
    const targets = part.head.concat(part.rest);
    if (!targets.length) return;
    targets.forEach((el) => {
      el.style.opacity = '0';
      el.style.transform = shift;
    });
    jobs.set(section, {
      head: part.head,
      rest: part.rest,
      targets,
      done: false,
      played: false,
      token: null,
      stop: null,
    });
    // No leave callback: inView drops the observer after the first enter,
    // so a section never hides again.
    inView(section, () => { play(section); }, { amount: 'some' });
  });

  window.addEventListener('hashchange', () => {
    const section = hashSection();
    if (section) showNow(section);
  });
  main.addEventListener('focusin', (event) => {
    const section = sectionOf(event.target);
    if (section) showNow(section);
  });
}
