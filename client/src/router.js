// client/src/router.js
import { createRouter, createWebHashHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'
import RoomView from './views/RoomView.vue'
import GameView from './views/GameView.vue'

const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/join/:roomCode', name: 'join', component: HomeView },
  { path: '/room/:id', name: 'room', component: RoomView },
  { path: '/room/:id/play', name: 'game', component: GameView },
]

export default createRouter({
  history: createWebHashHistory(),
  routes,
})
