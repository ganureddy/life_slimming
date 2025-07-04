
frappe.ui.form.on('Closing Checklist', {
    onload: function (frm) {
        let form_1 = document.getElementsByTagName('form')
        console.log(form_1, 'allforms')


        let form = document.getElementsByTagName('form')[3]
        form.style.width = "fit-content";
        form.style.textAlign = "left";
        form.style.whiteSpace = "nowrap";
        // form.style.fontSize = "medium";


        // form.style.margin = "auto";

        let col_6 = document.getElementsByClassName('col-sm-6')
        console.log(col_6[3], "col-6")
        col_6[3].style.textAlign = "end"



        let form10 = document.getElementsByTagName('form')[10]
        form10.style.textAlign = "center"
        form10.style.whiteSpace = "nowrap"
        let form8_1 = document.getElementsByTagName('form')[8].children;

        let form9_1 = document.getElementsByTagName('form')[9].children;
        // form9_1[0].style.textAlign = "center"

        let form8 = document.getElementsByTagName('form')[8]
        form8.style.textAlign = "center"
        form8.style.textAlign = "end"
        // form8.style.marginTop = "-1px";
        let form9 = document.getElementsByTagName('form')[9]
        form9.style.textAlign = "center"
        // form8_1[0].style.textAlign = "start";
        form8_1[0].style.justifyContent = "start";
        form8.style.marginTop = "-1px"

        let form11 = document.getElementsByTagName('form')[11]
        form11.style.textAlign = "center"
        form11.style.textAlign = "end"

        form9_1[0].style.textAlign = "end";
        form9_1[0].style.justifyContent = "end";
        form9_1[0].textAlign = "center"

        let checkboxes = document.getElementsByClassName("checkbox");
        for (let i = 0; i < checkboxes.length; i++) {
            checkboxes[i].style.textAlign = "end";
        }

        // let form1 = document.getElementsByTagName('form')[8]
        // let form1childrens = document.getElementsByTagName('form')[8].children
        // form1.style.textAlign = "end"
        // form1.style.justifyContent = "end"
        // console.log(form1)

        // for (let i = 1; i < form1childrens.length; i++) {
        // 	console.log(form1childrens[i], "childrens")
        // 	form1childrens[i].style.marginRight = "30px"
        // }




        let form2 = document.getElementsByTagName('form')[7]
        form2.style.width = "max-content"
        form2.style.textAlign = "center"
        console.log(form2)


        let form4 = document.getElementsByTagName('form')[4];
        form4.style.textAlign = "end"
        let form5 = document.getElementsByTagName('form')[5];
        form5.style.marginTop = "-4px"
        form5.style.textAlign = "left"
        let form6_1 = document.getElementsByTagName('form')[6];
        form6_1.style.textAlign = "center"
        form6_1.style.textAlignLast = "end";
        let form7 = document.getElementsByTagName('form')[7].children;
        // form7.style.width = "fit-content"
        for (let i = 1; i < form7.length; i++) {
            console.log(form7[i], "fomr7")
            form7[i].style.width = "fit-content"
        }


        let form13 = document.getElementsByTagName('form')[13].children;
        console.log(form13, 'form13333333333333333333333333333')

        for (let i = 0; i < form13.length; i++) {
            console.log(form7[i], "fomr13")
            form13[i].style.textAlign = "end";
            form13[i].style.textAlign = "left";
        }

        let form14 = document.getElementsByTagName('form')[14];
        form14.style.textAlignLast = "end";
        // for (let i = 1; i < form13.length; i++) {
        // 	// console.log(form7[i], "fomr13")
        // 	// form13[i].style.textAlign = "end";
        // 	form14[i].style.marginLeft = "35px";
        // }

        // console.log(form14, 'form14')
        // console.log(form14[1], 'form140000000000000000000000')

        // console.log(for14[0], 'form14')

        // let form12 = document.getElementsByTagName('form')[12].children;
        // console.log(form12, 'form1222222222222222222222222222')
        // for (let i = 0; i < form12.length; i++) {
        // 	console.log(form12[i], "fomr13")
        // 	form13[i].style.width = "fit-content";
        // }

        // Select the element containing the heading "completed1"
        // let headingElement = form13.querySelector(".control-label:contains('Completed1')");
        // console.log(headingElement, 'headingElement')
        // if (headingElement) {
        // 	// Align the heading to the right
        // 	headingElement.style.textAlign = "end";
        // }

        form4.style.whiteSpace = "nowrap"
        // form4.style.float = "left";
        // form4.style.marginRight = "20px";
        // form5.style.float = "right";
        // form5.style.float = "right";
        // form5.style.marginLeft = "20px";
        for (let i = 0; i <= form5.length; i++) {
            // form8[i].getElementsByClassName("frappe-control").style.margin = "0px"
            // form5.style.marginTop = "-24px";
        }

        let tab_content = document.getElementsByClassName("tab-content")
        console.log("tab-content", tab_content)
        tab_content[0].style.paddingBottom = "20px"


        let form_4 = document.getElementsByTagName('form')[4].children;
        for (let i = 1; i <= form_4.length; i++) {
            console.log(form_4[i], "Form-4444")
            form_4[i].style.width = "fit-content";
        }

        // margin-top: -24px;


        let forms = document.getElementsByTagName('form')[4]
        console.log(forms)
        forms.style.whiteSpace = "nowrap";
        // forms.style.marginLeft = "421px";
        // forms.style.marginTop = "17px";
        // forms.style.textAlign = "end";




        // let clearfix = document.getElementsByClassName("clearfix")[8]
        // clearfix.style.display = "none"
        // console.log(clearfix, ":hhh")
        let form4_1 = document.getElementsByTagName('form')[4].children
        let head2 = form4_1[0].getElementsByTagName("h5")
        head[0].style.marginBottom = "0px"

        let form6 = document.getElementsByTagName('form')[6].children
        // form6.style.textAlign = "center"
        // console.log(form6[0])
        let head = form6[0].getElementsByTagName("h4")
        // head.style.textAlign = "center"
        // console.log(head[0], "heading")
        head[0].style.marginBottom = "0px"
        // form6.style.whiteSpace = "nowrap";

        // let form9 = document.getElementsByTagName('form')[9].children
        // console.log(form9)
        let head1 = form9[0].getElementsByTagName("h4")
        // console.log(head1, "heading")
        head1[0].style.marginBottom = "0px"

        let clearfix1 = do17pxcument.getElementsByClassName("clearfix")[16]
        clearfix1.style.display = "none"
        // console.log(clearfix1, ":hhh")



        // let form8 = document.getElementsByTagName('form')[8].children
        // console.log(form8, "form8")









        // let Allforms = document.getElementsByTagName('form'),


        // 	let form11 = document.getElementsByTagName('form')[11],
        // 	form11_1 = document.getElementsByTagName('form')[11].children
        // form11.style.textAlign = "center"
        // for (let i = 1; i <= form11_1.length; i++) {
        // 	form11_1[i].style.marginRight = "30px"
        // }

    }

});

function myFunction() {





    console.log('--------', document.getElementsByTagName("label"))
    var element2 = document.getElementsByClassName("col-sm-6");
    console.log(element2, "form11")
    element2[1].setAttribute("class", "form-column col-sm-10 ");



    setTimeout(() => {
        var element3 = document.getElementsByClassName("col-sm-6");
        element3[1].setAttribute("class", "col-sm-2");

        let check = document.getElementsByClassName("checkbox")
        for (let i = 0; i <= check.length; i++) {
            check[i].style.marginTop = "16px"
            check[i].style.marginLeft = "421px"
            check[i].style.textAlign = "end"


        }


    }, 10)

    setTimeout(() => {

        let inputs = document.getElementsByClassName('control-input-wrapper')
        for (let i = 0; i <= inputs.length; i++) {
            // inputs[0].style.marginTop = ""		
            console.log(i)
            if (inputs[i] == inputs[4]) {
                inputs[4].style.marginBottom = "20px"
            }
            // else {
            inputs[i].style.marginBottom = "-26px"
            // }
            // if (inputs[i] == inputs[8] ) {
            // 	inputs[8].style.marginBottom = "20px"
            // }

        }
    }, 10)


}
myFunction()

