<!-- client/src/views/GameView.vue -->
<template>
  <div class="game">
    <p>Game is running... phase: {{ roomStore.phase }}</p>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useRoomStore } from '../stores/room'
import { useWebSocket } from '../composables/useWebSocket'

const route = useRoute()
const roomStore = useRoomStore()

onMounted(() => {
  if (!roomStore.connected) {
    const { connect } = useWebSocket()
    connect(route.params.id, roomStore.myPlayerId, roomStore.myToken)
  }
})
</script>
