/* eslint-disable react-refresh/only-export-components */
import { Button, Checkbox, Input } from 'antd'

// the cards need a stable key, the requirements of the API have no id
let lastId = 0

export function newRequirement() {
  return { id: ++lastId, has_allergy: false, description: '' }
}

export function withIds(requirements) {
  return requirements.map((item) => ({ ...item, id: ++lastId }))
}

export function requirementsBody(requirements) {
  return requirements
    .filter((item) => item.description.trim())
    .map((item) => ({ has_allergy: item.has_allergy, description: item.description.trim() }))
}

function RequirementsEditor({ requirements, onChange }) {
  function update(id, changes) {
    onChange(requirements.map((item) => item.id === id ? { ...item, ...changes } : item))
  }

  return (
    <>
      {requirements.length > 0 && (
        <div className="requirement-list">
          {requirements.map((requirement, index) => (
            <article className="requirement-card" key={requirement.id}>
              <strong className="requirement-index">{index + 1}</strong>
              <label className="form-field">
                <span className="sr-only">Requirement {index + 1} description</span>
                <Input className="mh-control" value={requirement.description} placeholder={index === 0 ? 'e.g. 1 vegan, peanut allergy' : 'e.g. 2 vegetarians'} onChange={(event) => update(requirement.id, { description: event.target.value })} />
              </label>
              <Checkbox className="allergy-checkbox" checked={requirement.has_allergy} onChange={(event) => update(requirement.id, { has_allergy: event.target.checked })}>
                <span aria-hidden="true">⚠️ </span>This requirement involves an allergy
              </Checkbox>
              {requirements.length > 1 && <Button className="requirement-remove" type="text" htmlType="button" aria-label={`Remove requirement ${index + 1}`} onClick={() => onChange(requirements.filter((item) => item.id !== requirement.id))}>Remove</Button>}
            </article>
          ))}
          <Button className="requirement-add" type="dashed" htmlType="button" onClick={() => onChange([...requirements, newRequirement()])}>＋ Add requirement</Button>
        </div>
      )}
      <Checkbox checked={requirements.length === 0} onChange={(event) => onChange(event.target.checked ? [] : [newRequirement()])}>
        No dietary restrictions or allergies
      </Checkbox>
    </>
  )
}

export default RequirementsEditor
