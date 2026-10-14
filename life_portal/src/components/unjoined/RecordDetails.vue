<script setup>
import { computed, reactive } from 'vue';
import data from '../../data/unjoined.json';
import { visibleFields, childColumns, displayValue, dateText, sameOriginFile } from '../../lib/unjoined';
import ClientPhoto from './ClientPhoto.vue';
const props = defineProps({ part: { type: Object, required: true }, manager: Boolean });
const fields = computed(() => visibleFields(data.meta[props.part.doctype] || [], props.part.doc));
const failed = reactive(new Set());
const files = computed(() => (props.part.files || []).map(file => ({ ...file, url: sameOriginFile(file.file_url, window.location.origin) })).filter(file => file.url));
const show = (field, value) => displayValue(field, value, props.manager);
const isImage = url => /\.(png|jpe?g|gif|webp|bmp|avif)(?:[?#]|$)/i.test(url);
</script>

<template>
  <article class="uj-record-part">
    <ClientPhoto :value="part.doc.custom_client_photo_attach || part.doc.image" large />
    <h3>{{ part.doctype }} · {{ show('name', part.doc.name) }}</h3>
    <div class="uj-full-grid">
      <div v-for="field in fields" :key="field.fieldname" :class="{ 'uj-wide': Array.isArray(part.doc[field.fieldname]) }">
        <b>{{ field.label || field.fieldname }}</b>
        <div v-if="Array.isArray(part.doc[field.fieldname])" class="uj-scroll">
          <table><thead><tr><th v-for="key in childColumns(part.doc[field.fieldname])" :key="key">{{ key }}</th></tr></thead>
            <tbody><tr v-for="(row, index) in part.doc[field.fieldname]" :key="row.name || index"><td v-for="key in childColumns(part.doc[field.fieldname])" :key="key">{{ show(key, row[key]) }}</td></tr></tbody>
          </table>
        </div>
        <span v-else>{{ /Date/.test(field.fieldtype) ? dateText(part.doc[field.fieldname]) : show(field.fieldname, part.doc[field.fieldname]) }}</span>
      </div>
    </div>
    <h4>Attached images &amp; documents</h4>
    <p v-if="part.attachmentError" class="uj-error">{{ part.attachmentError }}</p>
    <div class="uj-gallery">
      <a v-for="file in files" :key="file.url" :href="file.url" target="_blank" rel="noopener">
        <img v-if="isImage(file.url) && !failed.has(file.url)" :src="file.url" loading="lazy" :alt="show('file_name', file.file_name || 'Attached image')" @error="failed.add(file.url)">
        <span>{{ failed.has(file.url) ? 'Image not attached' : show('file_name', file.file_name || 'Attachment') }}</span>
      </a>
      <div v-if="!files.length" class="uj-photo-empty">Image not attached</div>
    </div>
  </article>
</template>
