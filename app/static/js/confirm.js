// Ask before destructive actions. Forms opt in with data-confirm="question".
document.addEventListener("submit", function (event) {
  const question = event.target.dataset && event.target.dataset.confirm;
  if (question && !window.confirm(question)) event.preventDefault();
});
