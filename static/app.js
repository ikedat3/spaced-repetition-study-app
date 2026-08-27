const studyCard = document.getElementById("study-card");
const feedback = document.getElementById("feedback");

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

async function loadQuestion() {
  feedback.classList.add("hidden");
  const res = await fetch("/api/next-question");
  const data = await res.json();

  if (data.done) {
    studyCard.innerHTML = `<h2>完了</h2><p>${escapeHtml(data.message)}</p>`;
    return;
  }

  const card = data.card;
  if (card.format === "multiple_choice") {
    const options = card.options
      .map((opt) => `<button class="option-btn" data-answer="${escapeHtml(opt)}">${escapeHtml(opt)}</button>`)
      .join("");
    studyCard.innerHTML = `<h2>問題</h2><p>${escapeHtml(card.prompt)}</p><div class="option-list">${options}</div>`;

    studyCard.querySelectorAll(".option-btn").forEach((btn) => {
      btn.addEventListener("click", () => submitAnswer(card.id, btn.dataset.answer || ""));
    });
    return;
  }

  studyCard.innerHTML = `
    <h2>問題</h2>
    <p>${escapeHtml(card.prompt)}</p>
    <input id="free-answer" type="text" placeholder="回答を入力" />
    <button id="submit-answer">回答する</button>
  `;
  document.getElementById("submit-answer").addEventListener("click", () => {
    const value = document.getElementById("free-answer").value;
    submitAnswer(card.id, value);
  });
}

async function submitAnswer(cardId, userAnswer) {
  const res = await fetch("/api/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ card_id: cardId, user_answer: userAnswer }),
  });
  const data = await res.json();

  if (data.error) {
    feedback.classList.remove("hidden");
    feedback.innerHTML = `<p>${escapeHtml(data.error)}</p>`;
    return;
  }

  feedback.classList.remove("hidden");
  feedback.innerHTML = `
    <h3>${data.correct ? "正解" : "不正解"}</h3>
    <p><strong>正答:</strong> ${escapeHtml(data.correct_answer)}</p>
    <p><strong>解説:</strong> ${escapeHtml(data.explanation || "")}</p>
    <p><strong>次回復習:</strong> ${escapeHtml(data.next_review_at)}</p>
    <div class="rating-list">
      <button data-rating="again">Again</button>
      <button data-rating="hard">Hard</button>
      <button data-rating="good">Good</button>
      <button data-rating="easy">Easy</button>
    </div>
  `;

  feedback.querySelectorAll("button[data-rating]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await fetch("/api/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ card_id: cardId, user_answer: userAnswer, rating: btn.dataset.rating, correct: data.correct }),
      });
      loadQuestion();
    });
  });
}

if (studyCard) {
  loadQuestion();
}
