/*
  main.js - JavaScript shared by every page.

  For now it does one job: on small screens it opens and closes the
  navigation menu when the "Menu" button is clicked.

  Feature-specific scripts (symptoms.js, documents.js, medications.js) are
  added in Phase 2, when those pages get interactive parts.
*/

// Tell the CSS that JavaScript is working. The menu is only collapsed on
// small screens when this class is present, so if JavaScript ever fails to
// load, the links simply stay visible.
document.documentElement.classList.add("js");

// Find the two elements we need on the page.
const navToggle = document.querySelector(".nav-toggle");
const siteNav = document.querySelector(".site-nav");

if (navToggle && siteNav) {
  // Run this function every time the Menu button is clicked.
  navToggle.addEventListener("click", function () {
    // classList.toggle adds the class if it is missing and removes it if it
    // is present. It returns true when the class was just added.
    const isOpen = siteNav.classList.toggle("is-open");

    // Screen readers use aria-expanded to announce whether the menu is open.
    navToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
  });
}
