function capabilitiesjs(resource_type, switchable_classname) {
    'use strict';
    
    var defaults = {'computehost': {'node_type': 'compute_skylake'},
    		        'network': {'physical_network': 'physnet1'},
    		        'device': {'vendor': 'Raspberry Pi'}
    		        };

    var capabilityNames = [];
    var capabilityValues = {};

    var criteriaCounter = 0; // gives distinct values to the input names

    // initial load of names
    var xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            capabilityValues = JSON.parse(this.responseText)['extra_capabilities'];
            capabilityNames = Object.keys(capabilityValues);
            capabilityNames.sort();
            var props = document.getElementById('criteria-payload-' + resource_type).getAttribute('form_data');
            if(props && props != 'None'){
                props = JSON.parse(props);
                if (props[0] == 'and'){
                    props.shift();
                    for(var i = 0 ; i < props.length; i++){
                        addCriterionItem(props[i][1].replace(/\$/g,''));
                        }
                return;
                }

                var prop = props[1].replace(/\$/g,'')
                addCriterionItem(prop);
                return;
            }
            addCriterionItem(Object.keys(defaults[resource_type])[0]);
            setDefaultCapabilityValue();

        }
        // braodcase event
        var capability_loaded = new Event(resource_type + '_capability_loaded');
        document.dispatchEvent(capability_loaded);
    };
    xhr.open('GET', resource_type + '/extras.json', true);
    xhr.send();

    var crl = document.querySelector('#criteria-list-' + resource_type);
    crl.innerHTML = '';

    function setResourcePropertyValues(index){
        var props = document.getElementById('criteria-payload-' + resource_type).getAttribute('form_data');
        if(!props || props == 'None' || props.length == 0){
            setPropertyType(index, Object.values(defaults[resource_type])[0]);
            return;
        }
        props = JSON.parse(props);
        if (props[0] == 'and'){
            props.shift();
            setPropertyType(index, props[index][2]);
            setConditionalType(index, props[index][0]);
            return;
        }
        setPropertyType(index, props[2]);
        setConditionalType(index, props[0]);
    }

    function displayWarningIfEmpty() {
        var criteria = document.querySelectorAll('.criterion-' + resource_type);
        document.querySelector('#no-criteria-warning-' + resource_type).hidden = criteria.length !== 0;
    }

    function addCriterion(event) {
        addCriterionItem();
    }

    function addCriterionItem(prefilled_name) {
        var criterion = document.createElement('li');
        criterion.style = "list-style-type:none;"
        criterion.className = 'criterion-' + resource_type;
        criterion.innerHTML =
            '<select class="form-control cri-name">' +
                '<option disabled selected></option>' + // blank...select something else.
            '</select> ' +
            '<select class="form-control cri-equality">' +
                '<option value="eq" class=' + switchable_classname + '>=</option>' +
                '<option value="lt" class=' + switchable_classname + '>&lt;</option>' +
                '<option value="le" class=' + switchable_classname + '>&le;</option>' +
                '<option value="gt" class=' + switchable_classname + '>&gt;</option>' +
                '<option value="ge" class=' + switchable_classname + '>&ge;</option>' +
                '<option value="ne" class=' + switchable_classname + '>&ne;</option>' +
            '</select> '+
            '<select id="resource-' + resource_type + '" class="form-control cri-val">' +
                '<option disabled selected></option>' +
            '</select> ' +
            '<button class="btn btn-xs btn-danger cri-rm ' + switchable_classname + '">X</button>';

        var index = criteriaCounter;
        criteriaCounter = criteriaCounter + 1;

        var name_selector = criterion.querySelector('.cri-name');
        name_selector.id = 'criteria-' + resource_type + '-id-' + index;
        name_selector.name = 'criteria-' + resource_type + '-name-' + index;
        capabilityNames.forEach(function(cn) {
            var opt = new Option(cn, cn);
            opt.className = switchable_classname;
            name_selector.appendChild(opt);
        });
        name_selector.addEventListener('change', changeCriterionName, false);

        var equality_selector = criterion.querySelector('.cri-equality');
        equality_selector.name = 'criteria-' + resource_type + '-equality-' + index;
        equality_selector.id = 'criteria-' + resource_type + '-equality-' + index;

        var value_selector = criterion.querySelector('.cri-val');
        value_selector.id = 'criteria-' + resource_type + '-value-' + index;
        value_selector.name = 'criteria-' + resource_type + '-value-' + index;

        var remove_button = criterion.querySelector('.cri-rm');
        remove_button.addEventListener('click', removeCriterion, false);

        if (prefilled_name) {
            name_selector.value = prefilled_name;
            // setting value bypasses change event; fire manually.
            var event = new Event('change');
            name_selector.dispatchEvent(event);
        }

        document.querySelector('#no-criteria-warning-' + resource_type).hidden = true;
        crl.appendChild(criterion);
        var hr = document.createElement('hr');
        hr.style = "margin-top:5px;margin-bottom:5px;"
        crl.appendChild(hr);
    }

    function changeCriterionName(event) {
        var criterion = event.target.parentNode;
        var name_selector = event.target;
        var value_selector = criterion.querySelector('.cri-val');

        value_selector.innerHTML = '<option disabled selected></option>'; // clear
        fillCriteriaValues(value_selector, name_selector.value);
    }

    function fillCriteriaValues(element, name) {
        var values = capabilityValues[name];
        values.sort();
        values.forEach(function(cv) {
            var opt = new Option(cv, cv);
            opt.className = switchable_classname;
            element.appendChild(opt);
        });
        setResourcePropertyValues(element.id.slice(-1));
    }

    function setDefaultCapabilityValue(){
        var options = $("#criteria-" + resource_type + "-value-0");
        try {
          var resource_type_value = Object.values(defaults[resource_type])[0]
          options.find('[value="' + resource_type_value + '"]').attr("selected","selected");
        } catch(err) {
          console.error(err);
        }
    }

    function setPropertyType(index, propType){
        var options = $('#criteria-' + resource_type + '-value-' + index);
          options.find('[value="' + propType + '"]').attr("selected","selected");
    }

    function setConditionalType(index, resourceCondition){
        var resourceCondition = $('#criteria-' + resource_type + '-equality-' + index);
        var conditions = {"==":"eq","<":"lt","<=":"le",">":"gt",">=":"ge","!=":"ne"}
        try {
        	resourceCondition.find('[value="' + conditions[resourceCondition] + '"]').attr("selected","selected");
        } catch(err) {
          console.error(err);
        }
    }

    function removeCriterion(event) {
        var criterion = event.target.parentNode;
        criterion.parentNode.removeChild(criterion);
        displayWarningIfEmpty();
    }

    var addbutton = document.querySelector('#criteria-add-' + resource_type);
    addbutton.addEventListener("click", addCriterion, false);

    document.querySelector('#no-criteria-warning-' + resource_type).querySelectorAll('.cri-adder').forEach(function (elem) {
        elem.addEventListener("click", function (event) {
            addCriterionItem(elem.dataset.criName);
        });
    });
};
