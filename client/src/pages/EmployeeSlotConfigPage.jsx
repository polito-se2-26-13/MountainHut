import { useEffect, useMemo, useState } from 'react';
import { Link, Navigate } from 'react-router';
import { apiRequest } from '../api/api.js';
import { useAuth } from '../auth/AuthContext.jsx';

function localDateString() {
  const now = new Date();
  const localDate = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return localDate.toISOString().slice(0, 10);
}

function createTable(tableNumber = '', seats = 2) {
  return {
    id: globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`,
    tableNumber,
    seats,
  };
}

function readSlotsResponse(response) {
  if (Array.isArray(response)) return response;
  if (Array.isArray(response?.slots)) return response.slots;
  if (Array.isArray(response?.items)) return response.items;
  return [];
}

function slotId(slot) {
  return slot.slotId ?? slot.id;
}

function slotLabel(slot) {
  if (slot.label) return slot.label;
  const timeRange = [slot.startTime, slot.endTime].filter(Boolean).join('–');
  const tables = Array.isArray(slot.tables) ? slot.tables : [];
  const seats = tables.reduce((sum, table) => sum + Number(table.seats || 0), 0);
  const date = slot.date || slot.slotDate || '';
  return `${date} ${timeRange} (${tables.length} tables / ${seats} seats)`;
}

function EmployeeSlotConfigPage() {
  const { session } = useAuth();
  const [formData, setFormData] = useState({
    slotDate: localDateString(),
    startTime: '',
    endTime: '',
    mealType: '',
    tables: [],
  });
  const [copySourceOptions, setCopySourceOptions] = useState([]);
  const [selectedSourceSlotId, setSelectedSourceSlotId] = useState('');
  const [isLoadingSources, setIsLoadingSources] = useState(false);
  const [isCopying, setIsCopying] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [sourceRefreshKey, setSourceRefreshKey] = useState(0);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    if (!session?.isAuthenticated || session.userProfile.role !== 'Employee') return undefined;
    let active = true;
    queueMicrotask(() => {
      if (active) {
        setIsLoadingSources(true);
        setCopySourceOptions([]);
        setSelectedSourceSlotId('');
      }
    });
    apiRequest(`/slots?date=${encodeURIComponent(formData.slotDate)}`, {
      headers: { Authorization: `Bearer ${session.token}` },
    })
      .then(result => {
        if (active) setCopySourceOptions(readSlotsResponse(result));
      })
      .catch(error => {
        if (active) setErrorMessage(error.message || 'Could not load saved time slots.');
      })
      .finally(() => {
        if (active) setIsLoadingSources(false);
      });
    return () => {
      active = false;
    };
  }, [formData.slotDate, session, sourceRefreshKey]);

  const totalCapacity = useMemo(
    () => formData.tables.reduce((total, table) => total + (Number(table.seats) || 0), 0),
    [formData.tables]
  );

  if (!session?.isAuthenticated || session.userProfile.role !== 'Employee') {
    return <Navigate to="/login" replace />;
  }

  function updateForm(field, value) {
    setFormData(current => ({ ...current, [field]: value }));
    setErrorMessage('');
    setSuccessMessage('');
  }

  function updateTable(tableId, field, value) {
    setFormData(current => ({
      ...current,
      tables: current.tables.map(table =>
        table.id === tableId ? { ...table, [field]: value } : table
      ),
    }));
    setErrorMessage('');
    setSuccessMessage('');
  }

  function addTable() {
    setFormData(current => ({ ...current, tables: [...current.tables, createTable()] }));
    setErrorMessage('');
    setSuccessMessage('');
  }

  function removeTable(tableId) {
    setFormData(current => ({
      ...current,
      tables: current.tables.filter(table => table.id !== tableId),
    }));
    setErrorMessage('');
    setSuccessMessage('');
  }

  async function copyTables() {
    if (!selectedSourceSlotId) {
      setErrorMessage('Choose a saved time slot to copy first.');
      return;
    }
    const source = copySourceOptions.find(
      slot => String(slotId(slot)) === String(selectedSourceSlotId)
    );
    if (!source) {
      setErrorMessage('The selected saved time slot is no longer available.');
      return;
    }
    setIsCopying(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      const sourceTables = source.tables;
      if (!Array.isArray(sourceTables))
        throw new Error('The selected time slot has no table configuration.');
      setFormData(current => ({
        ...current,
        tables: sourceTables.map(table =>
          createTable(String(table.tableNumber ?? ''), Number(table.seats) || 1)
        ),
      }));
      setSuccessMessage(
        `Copied ${sourceTables.length} table${sourceTables.length === 1 ? '' : 's'} from the selected time slot.`
      );
    } catch (error) {
      setErrorMessage(error.message || 'Could not copy the saved table configuration.');
    } finally {
      setIsCopying(false);
    }
  }

  function validate() {
    if (!formData.slotDate || !formData.startTime || !formData.endTime)
      return 'Date, start time, and end time are required.';
    if (formData.startTime >= formData.endTime) return 'End time must be later than start time.';
    if (formData.tables.length === 0) return 'Add at least one table to this time slot.';
    if (formData.tables.some(table => !String(table.tableNumber).trim()))
      return 'Enter a number for every table.';
    if (
      formData.tables.some(
        table => !Number.isInteger(Number(table.seats)) || Number(table.seats) < 1
      )
    )
      return 'Each table must have at least one seat.';
    const numbers = formData.tables.map(table => String(table.tableNumber).trim().toLowerCase());
    if (new Set(numbers).size !== numbers.length)
      return 'Table numbers must be unique within this time slot.';
    return '';
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitted(true);
    setErrorMessage('');
    setSuccessMessage('');
    const validationMessage = validate();
    if (validationMessage) {
      setErrorMessage(validationMessage);
      return;
    }

    setIsSaving(true);
    try {
      const result = await apiRequest('/slots', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.token}`,
        },
        body: JSON.stringify({
          date: formData.slotDate,
          startTime: formData.startTime,
          endTime: formData.endTime,
          ...(formData.mealType ? { mealType: formData.mealType } : {}),
          tables: formData.tables.map(({ tableNumber, seats }) => ({
            tableNumber: String(tableNumber).trim(),
            seats: Number(seats),
          })),
        }),
      });
      setSuccessMessage(result?.message || 'Time slot and table configuration saved.');
      setSubmitted(false);
      setSourceRefreshKey(current => current + 1);
    } catch (error) {
      setErrorMessage(error.message || 'Could not save this time slot.');
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <main className="page slot-page">
      <header className="slot-page-header">
        <div>
          <Link className="back-link" to="/home/employee">
            Employee home
          </Link>
          <p className="eyebrow">MOUNTAINHUT · EMPLOYEE TOOLS</p>
          <h1>Service slots &amp; table setup</h1>
          <p className="form-intro">Set service times and build a table layout for any date.</p>
        </div>
        <div className="capacity-card" aria-live="polite">
          <span>Total capacity</span>
          <strong>{totalCapacity}</strong>
          <small>seats in this slot</small>
        </div>
      </header>

      {errorMessage && (
        <div className="form-alert error-alert" role="alert">
          {errorMessage}
        </div>
      )}
      {successMessage && (
        <div className="form-alert success-alert" role="status">
          {successMessage}
        </div>
      )}

      <form className="slot-form" onSubmit={handleSubmit} noValidate>
        <section className="slot-panel" aria-labelledby="slot-details-title">
          <div className="section-heading">
            <div>
              <span className="section-step">01</span>
              <h2 id="slot-details-title">Service time</h2>
            </div>
            <p>Create multiple service rounds on the same date.</p>
          </div>

          <div className="slot-form-grid">
            <label className="form-field">
              <span>
                Date{' '}
                <span className="required-mark" aria-hidden="true">
                  *
                </span>
              </span>
              <input
                type="date"
                required
                value={formData.slotDate}
                onChange={event => updateForm('slotDate', event.target.value)}
              />
            </label>
            <label className="form-field">
              <span>
                Starting time{' '}
                <span className="required-mark" aria-hidden="true">
                  *
                </span>
              </span>
              <input
                type="time"
                required
                value={formData.startTime}
                onChange={event => updateForm('startTime', event.target.value)}
              />
            </label>
            <label className="form-field">
              <span>
                Ending time{' '}
                <span className="required-mark" aria-hidden="true">
                  *
                </span>
              </span>
              <input
                type="time"
                required
                value={formData.endTime}
                onChange={event => updateForm('endTime', event.target.value)}
              />
            </label>
            <label className="form-field">
              <span>
                Meal type <span className="optional-mark">(optional)</span>
              </span>
              <select
                value={formData.mealType}
                onChange={event => updateForm('mealType', event.target.value)}
              >
                <option value="">Select a meal type</option>
                <option value="Lunch">Lunch</option>
                <option value="Dinner">Dinner</option>
                <option value="Snack">Snack</option>
              </select>
            </label>
          </div>
        </section>

        <section className="slot-panel" aria-labelledby="tables-title">
          <div className="section-heading">
            <div>
              <span className="section-step">02</span>
              <h2 id="tables-title">Tables &amp; seats</h2>
            </div>
            <p>Choose a layout that fits this date and service.</p>
          </div>

          <div className="copy-toolbar">
            <label className="form-field copy-select-field">
              <span>Copy the tables of a previous slot</span>
              <select
                value={selectedSourceSlotId}
                onChange={event => setSelectedSourceSlotId(event.target.value)}
                disabled={isLoadingSources || copySourceOptions.length === 0}
              >
                <option value="">
                  {isLoadingSources
                    ? 'Loading saved slots…'
                    : copySourceOptions.length
                      ? 'Choose a saved time slot'
                      : 'No saved slots for this date'}
                </option>
                {copySourceOptions.map((slot, index) => (
                  <option key={slotId(slot) ?? index} value={slotId(slot)}>
                    {slotLabel(slot)}
                  </option>
                ))}
              </select>
            </label>
            <button
              className="secondary-button copy-button"
              type="button"
              onClick={copyTables}
              disabled={isCopying || isLoadingSources || !copySourceOptions.length}
            >
              {isCopying ? 'Copying…' : 'Copy table configuration'}
            </button>
          </div>

          <div className="table-list-heading" aria-hidden="true">
            <span>Table number</span>
            <span>Seats</span>
            <span />
          </div>
          {formData.tables.length === 0 ? (
            <div className="empty-tables">
              <strong>No tables added yet</strong>
              <span>Add a table or copy a saved configuration to get started.</span>
            </div>
          ) : (
            <div className="table-list">
              {formData.tables.map((table, index) => (
                <div className="table-row" key={table.id}>
                  <span className="table-index">{String(index + 1).padStart(2, '0')}</span>
                  <label className="sr-only" htmlFor={`table-number-${table.id}`}>
                    Table number {index + 1}
                  </label>
                  <input
                    id={`table-number-${table.id}`}
                    value={table.tableNumber}
                    placeholder="e.g. T1"
                    onChange={event => updateTable(table.id, 'tableNumber', event.target.value)}
                    aria-label={`Table number ${index + 1}`}
                  />
                  <label className="sr-only" htmlFor={`table-seats-${table.id}`}>
                    Seats at table {index + 1}
                  </label>
                  <input
                    id={`table-seats-${table.id}`}
                    type="number"
                    min="1"
                    step="1"
                    value={table.seats}
                    onChange={event => updateTable(table.id, 'seats', event.target.value)}
                    aria-label={`Seats at table ${index + 1}`}
                  />
                  <button
                    className="remove-table-button"
                    type="button"
                    onClick={() => removeTable(table.id)}
                    aria-label={`Remove table ${index + 1}`}
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
          <button className="add-table-button" type="button" onClick={addTable}>
            + Add a table
          </button>
          {submitted && errorMessage && (
            <p className="slot-validation-note">Review the time and table details above.</p>
          )}
        </section>

        <footer className="slot-form-footer">
          <span>Changes are saved to the selected date and time.</span>
          <button className="submit-button save-slot-button" type="submit" disabled={isSaving}>
            {isSaving ? 'Saving configuration…' : 'Save time slot'}
          </button>
        </footer>
      </form>
    </main>
  );
}

export default EmployeeSlotConfigPage;
