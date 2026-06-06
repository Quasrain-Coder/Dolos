<template>
  <div class="answer-input">
    <div class="question-card">
      <div class="label">这道题是</div>
      <div class="term">{{ gameStore.questionTerm }}</div>
      <div class="hint">写出一个能骗过别人的假定义</div>
    </div>

    <div v-if="!gameStore.answerSubmitted">
      <textarea
        v-model="answer"
        class="textarea"
        placeholder="输入你的假定义..."
        maxlength="200"
      ></textarea>
      <button class="btn btn-primary btn-lg" :disabled="!answer.trim()" @click="submitAnswer">提交答案</button>
    </div>

    <div v-else class="submitted-card">
      <p>✅ 已提交，等待其他玩家...</p>
      <p class="your-answer">「{{ gameStore.myAnswer }}」</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useGameStore } from '../stores/game'
import { useWebSocket } from '../composables/useWebSocket'

const gameStore = useGameStore()
const { send } = useWebSocket()
const answer = ref('')

function submitAnswer() {
  if (!answer.value.trim()) return
  gameStore.myAnswer = answer.value.trim()
  send('submit_answer', { text: gameStore.myAnswer })
}
</script>
