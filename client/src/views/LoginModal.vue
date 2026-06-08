<!-- client/src/views/LoginModal.vue -->
<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="login-modal">
      <div class="modal-header">
        <h3>{{ tab === 'login' ? '登录' : '注册' }}</h3>
        <button class="modal-close" @click="$emit('close')">✕</button>
      </div>

      <div class="tab-bar">
        <button
          :class="{ active: tab === 'login' }"
          @click="tab = 'login'"
        >登录</button>
        <button
          :class="{ active: tab === 'register' }"
          @click="tab = 'register'"
        >注册</button>
      </div>

      <form @submit.prevent="handleSubmit" class="modal-form">
        <input
          v-model="username"
          class="input"
          placeholder="用户名"
          maxlength="20"
          required
        />
        <input
          v-model="password"
          class="input"
          type="password"
          placeholder="密码"
          required
        />
        <p v-if="roomStore.authError" class="error">{{ roomStore.authError }}</p>
        <button type="submit" class="btn btn-primary" :disabled="!username.trim() || !password">
          {{ tab === 'login' ? '登录' : '注册' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoomStore } from '../stores/room'

defineProps({ visible: Boolean })
const emit = defineEmits(['close'])

const roomStore = useRoomStore()
const tab = ref('login')
const username = ref('')
const password = ref('')

async function handleSubmit() {
  let ok
  if (tab.value === 'login') {
    ok = await roomStore.login(username.value.trim(), password.value)
  } else {
    ok = await roomStore.register(username.value.trim(), password.value)
  }
  if (ok) {
    emit('close')
    username.value = ''
    password.value = ''
  }
}
</script>
