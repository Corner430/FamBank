<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api, getStoredUser, ApiError } from '../services/api'
import ChildSelector from '../components/ChildSelector.vue'

interface WishItem {
  id: number
  name: string
  registered_price: string
  current_price: string
  last_price_update: string | null
  verification_url: string | null
}

interface WishListData {
  id: number
  status: string
  registered_at: string
  lock_until: string
  valid_until: string
  avg_price: string
  max_price: string
  p_active: string
  active_target_item_id: number | null
  items: WishItem[]
}

interface PurchaseResult {
  item_name: string
  actual_cost: string
  deduction: { from_principal: string; from_interest: string }
  b_principal_after: string
  b_interest_pool_after: string
  transaction_ids: number[]
  is_substitute: boolean
}

const user = computed(() => getStoredUser())
const isParent = computed(() => user.value?.role === 'parent')

const childId = ref<number | null>(null)
const wishList = ref<WishListData | null>(null)
const loading = ref(true)
const error = ref('')
const successMsg = ref('')

// New item form
const showAddForm = ref(false)
const newItems = ref<{ name: string; price: string; verification_url: string }[]>([
  { name: '', price: '', verification_url: '' },
])

// Price update
const editingPriceItemId = ref<number | null>(null)
const newPrice = ref('')
const creating = ref(false)

// Purchase
const purchasingItemId = ref<number | null>(null)
const purchaseCost = ref('')
const purchaseIsSubstitute = ref(false)
const purchaseDescription = ref('')
const purchaseResult = ref<PurchaseResult | null>(null)

const lockDaysRemaining = computed(() => {
  if (!wishList.value) return 0
  const lock = new Date(wishList.value.lock_until)
  const now = new Date()
  const diff = Math.ceil((lock.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
  return Math.max(0, diff)
})

const isLocked = computed(() => lockDaysRemaining.value > 0)

function childParam(): string {
  return isParent.value && childId.value ? `?child_id=${childId.value}` : ''
}

function onChildSelect(id: number) {
  childId.value = id
  loadWishList()
}

async function loadWishList() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get<WishListData | null>(`/wishlist${childParam()}`)
    wishList.value = res
  } catch (e: unknown) {
    error.value = e instanceof ApiError ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

function addItemRow() {
  newItems.value.push({ name: '', price: '', verification_url: '' })
}

function removeItemRow(index: number) {
  if (newItems.value.length > 1) {
    newItems.value.splice(index, 1)
  }
}

async function createWishList() {
  error.value = ''
  successMsg.value = ''
  const items = newItems.value.filter(i => i.name && i.price)
  if (items.length === 0) {
    error.value = '请至少填写一个愿望物品'
    return
  }

  creating.value = true
  try {
    const body: Record<string, unknown> = { items }
    if (isParent.value && childId.value) {
      body.child_id = childId.value
    }
    const res = await api.post<WishListData>('/wishlist', body)
    wishList.value = res
    showAddForm.value = false
    newItems.value = [{ name: '', price: '', verification_url: '' }]
    successMsg.value = '愿望清单创建成功'
  } catch (e: unknown) {
    error.value = e instanceof ApiError ? e.message : '创建失败'
  } finally {
    creating.value = false
  }
}

async function updatePrice(itemId: number) {
  error.value = ''
  successMsg.value = ''
  if (!newPrice.value) return

  try {
    await api.patch(`/wishlist/items/${itemId}/price${childParam()}`, { price: newPrice.value })
    editingPriceItemId.value = null
    newPrice.value = ''
    successMsg.value = '价格更新成功'
    await loadWishList()
  } catch (e: unknown) {
    error.value = e instanceof ApiError ? e.message : '更新失败'
  }
}

async function declareTarget(itemId: number) {
  error.value = ''
  successMsg.value = ''
  try {
    const body: Record<string, unknown> = { wish_item_id: itemId }
    if (isParent.value && childId.value) {
      body.child_id = childId.value
    }
    await api.post('/wishlist/declare-target', body)
    successMsg.value = '目标已设定'
    await loadWishList()
  } catch (e: unknown) {
    error.value = e instanceof ApiError ? e.message : '设定失败'
  }
}

async function clearTarget() {
  error.value = ''
  successMsg.value = ''
  try {
    await api.delete(`/wishlist/declare-target${childParam()}`)
    successMsg.value = '目标已清除，P_active恢复为最高价'
    await loadWishList()
  } catch (e: unknown) {
    error.value = e instanceof ApiError ? e.message : '清除失败'
  }
}

async function executePurchase(itemId: number) {
  error.value = ''
  successMsg.value = ''
  purchaseResult.value = null
  if (!purchaseCost.value) {
    error.value = '请输入购买金额'
    return
  }

  try {
    const body: Record<string, unknown> = {
      wish_item_id: itemId,
      actual_cost: purchaseCost.value,
      is_substitute: purchaseIsSubstitute.value,
      description: purchaseDescription.value,
    }
    if (isParent.value && childId.value) {
      body.child_id = childId.value
    }
    const res = await api.post<PurchaseResult>('/accounts/b/purchase', body)
    purchaseResult.value = res
    purchasingItemId.value = null
    purchaseCost.value = ''
    purchaseIsSubstitute.value = false
    purchaseDescription.value = ''
    successMsg.value = `购买成功: ${res.item_name}`
    await loadWishList()
  } catch (e: unknown) {
    error.value = e instanceof ApiError ? e.message : '购买失败'
  }
}

onMounted(loadWishList)
</script>

<template>
  <div class="wishlist-page">
    <h1>愿望清单</h1>

    <ChildSelector v-if="isParent" @select="onChildSelect" />

    <p v-if="loading">加载中...</p>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="successMsg" class="success">{{ successMsg }}</p>

    <!-- No active wish list -->
    <div v-if="!loading && !wishList">
      <p>暂无愿望清单</p>
      <button @click="showAddForm = true" v-if="!showAddForm">创建愿望清单</button>
    </div>

    <!-- Active wish list -->
    <div v-if="wishList" class="wish-list-info">
      <div class="stats">
        <div class="stat">
          <span class="label">状态</span>
          <span class="value">{{ wishList.status === 'active' ? '生效中' : wishList.status }}</span>
        </div>
        <div class="stat">
          <span class="label">P_active</span>
          <span class="value">&yen;{{ wishList.p_active }}</span>
        </div>
        <div class="stat">
          <span class="label">均价</span>
          <span class="value">&yen;{{ wishList.avg_price }}</span>
        </div>
        <div class="stat">
          <span class="label">最高价</span>
          <span class="value">&yen;{{ wishList.max_price }}</span>
        </div>
        <div class="stat" :class="{ locked: isLocked }">
          <span class="label">锁定期</span>
          <span class="value" v-if="isLocked">剩余 {{ lockDaysRemaining }} 天</span>
          <span class="value" v-else>已解锁</span>
        </div>
        <div class="stat">
          <span class="label">有效期至</span>
          <span class="value">{{ wishList.valid_until }}</span>
        </div>
      </div>

      <!-- Target controls -->
      <div class="target-controls" v-if="wishList.active_target_item_id">
        <span>当前目标物品 ID: {{ wishList.active_target_item_id }}</span>
        <button class="btn-small btn-secondary" @click="clearTarget">清除目标</button>
      </div>

      <!-- Items table -->
      <table class="items-table">
        <thead>
          <tr>
            <th>物品</th>
            <th>注册价</th>
            <th>当前价</th>
            <th>上次更新</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in wishList.items" :key="item.id"
              :class="{ 'is-target': item.id === wishList.active_target_item_id }">
            <td>
              {{ item.name }}
              <span v-if="item.id === wishList.active_target_item_id" class="target-badge">目标</span>
              <a v-if="item.verification_url" :href="item.verification_url" target="_blank" class="link-icon">链接</a>
            </td>
            <td>&yen;{{ item.registered_price }}</td>
            <td>&yen;{{ item.current_price }}</td>
            <td>{{ item.last_price_update || '-' }}</td>
            <td class="actions">
              <!-- Price update -->
              <template v-if="editingPriceItemId === item.id">
                <input v-model="newPrice" type="text" inputmode="decimal" placeholder="新价格" class="price-input" />
                <button class="btn-small" @click="updatePrice(item.id)">确认</button>
                <button class="btn-small btn-secondary" @click="editingPriceItemId = null">取消</button>
              </template>
              <button v-else class="btn-small" @click="editingPriceItemId = item.id; newPrice = ''">改价</button>

              <!-- Declare target -->
              <button v-if="item.id !== wishList.active_target_item_id"
                      class="btn-small btn-secondary"
                      @click="declareTarget(item.id)">设为目标</button>

              <!-- Purchase -->
              <template v-if="purchasingItemId === item.id">
                <div class="purchase-form">
                  <input v-model="purchaseCost" type="text" inputmode="decimal" placeholder="实付金额" class="price-input" />
                  <label class="substitute-label">
                    <input type="checkbox" v-model="purchaseIsSubstitute" /> 替代品
                  </label>
                  <input v-model="purchaseDescription" type="text" placeholder="备注" class="desc-input" />
                  <button class="btn-small btn-buy" @click="executePurchase(item.id)">确认购买</button>
                  <button class="btn-small btn-secondary" @click="purchasingItemId = null">取消</button>
                </div>
              </template>
              <button v-else class="btn-small btn-buy" @click="purchasingItemId = item.id; purchaseCost = item.current_price; purchaseIsSubstitute = false; purchaseDescription = ''">购买</button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Replace list button -->
      <div class="replace-section" v-if="!isLocked">
        <button @click="showAddForm = true" v-if="!showAddForm">替换清单</button>
      </div>
    </div>

    <!-- Purchase result -->
    <div v-if="purchaseResult" class="purchase-result">
      <h3>购买完成</h3>
      <p>物品: {{ purchaseResult.item_name }}</p>
      <p>实付: &yen;{{ purchaseResult.actual_cost }}</p>
      <p>本金扣除: &yen;{{ purchaseResult.deduction.from_principal }}</p>
      <p>利息池扣除: &yen;{{ purchaseResult.deduction.from_interest }}</p>
      <p>B本金余额: &yen;{{ purchaseResult.b_principal_after }}</p>
      <p>B利息池余额: &yen;{{ purchaseResult.b_interest_pool_after }}</p>
    </div>

    <!-- Create wish list form -->
    <div v-if="showAddForm" class="add-form">
      <h2>{{ wishList ? '替换愿望清单' : '创建愿望清单' }}</h2>
      <div v-for="(item, index) in newItems" :key="index" class="item-row">
        <input v-model="item.name" type="text" placeholder="物品名称" />
        <input v-model="item.price" type="text" inputmode="decimal" placeholder="价格（元）" />
        <input v-model="item.verification_url" type="text" placeholder="验证链接（可选）" />
        <button class="btn-small btn-secondary" @click="removeItemRow(index)" v-if="newItems.length > 1">删除</button>
      </div>
      <div class="form-actions">
        <button class="btn-small" @click="addItemRow">添加物品</button>
        <button @click="createWishList" :disabled="creating">{{ creating ? '提交中...' : '提交' }}</button>
        <button class="btn-secondary" @click="showAddForm = false" :disabled="creating">取消</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wishlist-page {
  max-width: 800px;
}

.error {
  color: #e74c3c;
  padding: 8px;
  background: #ffeaea;
  border-radius: 4px;
}

.success {
  color: #27ae60;
  padding: 8px;
  background: #eafff0;
  border-radius: 4px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.stat {
  background: #f5f5f5;
  padding: 12px;
  border-radius: 6px;
}

.stat.locked {
  background: #fff3e0;
}

.stat .label {
  display: block;
  font-size: 0.8em;
  color: #888;
  margin-bottom: 4px;
}

.stat .value {
  font-size: 1.1em;
  font-weight: 600;
}

.target-controls {
  margin-bottom: 16px;
  padding: 8px 12px;
  background: #e3f2fd;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.items-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 16px;
}

.items-table th,
.items-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.items-table th {
  font-weight: 600;
  color: #555;
  background: #fafafa;
}

.is-target {
  background: #e8f5e9;
}

.target-badge {
  display: inline-block;
  background: #4caf50;
  color: white;
  font-size: 0.7em;
  padding: 2px 6px;
  border-radius: 3px;
  margin-left: 6px;
}

.link-icon {
  font-size: 0.8em;
  margin-left: 6px;
  color: #4a90d9;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.price-input {
  width: 80px;
  padding: 4px 6px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.9em;
}

.desc-input {
  width: 100px;
  padding: 4px 6px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.9em;
}

.purchase-form {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.substitute-label {
  font-size: 0.85em;
  display: flex;
  align-items: center;
  gap: 4px;
}

button {
  padding: 8px 16px;
  background: #4a90d9;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95em;
}

button:hover {
  opacity: 0.9;
}

.btn-small {
  padding: 4px 10px;
  font-size: 0.85em;
}

.btn-secondary {
  background: #95a5a6;
}

.btn-buy {
  background: #27ae60;
}

.purchase-result {
  margin-top: 16px;
  padding: 16px;
  background: #e8f5e9;
  border-radius: 8px;
}

.purchase-result h3 {
  margin-top: 0;
}

.add-form {
  margin-top: 20px;
  padding: 16px;
  background: #f9f9f9;
  border-radius: 8px;
}

.add-form h2 {
  margin-top: 0;
  font-size: 1.1em;
}

.item-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.item-row input {
  padding: 8px 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.95em;
}

.item-row input:first-child {
  flex: 2;
}

.item-row input:nth-child(2) {
  flex: 1;
}

.item-row input:nth-child(3) {
  flex: 2;
}

.form-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.replace-section {
  margin-top: 16px;
}
</style>
