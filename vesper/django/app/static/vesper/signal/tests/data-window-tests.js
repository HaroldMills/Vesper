import { DataWindow } from '../data-window.js';


const _TEST_CASES = new Map([

    ['Blackman', [DataWindow.createBlackmanWindow, [

        [],
        [0],
        [0, 0],
        [0, 1, 0],
        [0, .63, .63, 0],
        [0, .34, 1, .34, 0],

        // size 100, from scipy.signal.get_window
        [-1.3877787807814457e-17, 3.6304679052144573e-04, 1.4584896963108218e-03,
         3.3050860099324703e-03, 5.9335994674046544e-03, 9.3860617320119799e-03,
         1.3714756540369306e-02, 1.8980944223451167e-02, 2.5253348873947708e-02,
         3.2606434624560324e-02, 4.1118501260732659e-02, 5.0869632653865432e-02,
         6.1939534213364275e-02, 7.4405297672890849e-02, 8.8339133012523580e-02,
         1.0380610814900720e-01, 1.2086193718628682e-01, 1.3955085750436985e-01,
         1.5990363478343400e-01, 1.8193573323000373e-01, 2.0564568582147591e-01,
         2.3101369635289254e-01, 2.5800050150366216e-01, 2.8654651709866197e-01,
         3.1657128828228220e-01, 3.4797325852674926e-01, 3.8062986733428278e-01,
         4.1439798124748289e-01, 4.4911465743802986e-01, 4.8459823378621947e-01,
         5.2064973407928783e-01, 5.5705457183005869e-01, 5.9358453133187383e-01,
         6.3000000000000023e-01, 6.6605242187760483e-01, 7.0148693847363075e-01,
         7.3604517991077978e-01, 7.6946816674637608e-01, 8.0149928082995836e-01,
         8.3188726221214804e-01, 8.6038918844226620e-01, 8.8677339259930321e-01,
         9.1082227709315766e-01, 9.3233498164060546e-01, 9.5112986584247239e-01,
         9.6704676943374324e-01, 9.7994901650563326e-01, 9.8972513375747284e-01,
         9.9629025706755892e-01, 9.9958720530934331e-01, 9.9958720530934331e-01,
         9.9629025706755892e-01, 9.8972513375747273e-01, 9.7994901650563326e-01,
         9.6704676943374313e-01, 9.5112986584247239e-01, 9.3233498164060524e-01,
         9.1082227709315766e-01, 8.8677339259930310e-01, 8.6038918844226620e-01,
         8.3188726221214770e-01, 8.0149928082995836e-01, 7.6946816674637586e-01,
         7.3604517991077978e-01, 7.0148693847363042e-01, 6.6605242187760483e-01,
         6.2999999999999967e-01, 5.9358453133187350e-01, 5.5705457183005858e-01,
         5.2064973407928783e-01, 4.8459823378621902e-01, 4.4911465743802959e-01,
         4.1439798124748278e-01, 3.8062986733428278e-01, 3.4797325852674893e-01,
         3.1657128828228198e-01, 2.8654651709866197e-01, 2.5800050150366227e-01,
         2.3101369635289232e-01, 2.0564568582147583e-01, 1.8193573323000373e-01,
         1.5990363478343378e-01, 1.3955085750436971e-01, 1.2086193718628682e-01,
         1.0380610814900720e-01, 8.8339133012523385e-02, 7.4405297672890752e-02,
         6.1939534213364275e-02, 5.0869632653865432e-02, 4.1118501260732618e-02,
         3.2606434624560275e-02, 2.5253348873947708e-02, 1.8980944223451167e-02,
         1.3714756540369251e-02, 9.3860617320119799e-03, 5.9335994674046544e-03,
         3.3050860099324147e-03, 1.4584896963108357e-03, 3.6304679052139022e-04,
         -1.3877787807814457e-17],

        // size 101, from scipy.signal.get_window
        [-1.3877787807814457e-17, 3.5581189102243393e-04, 1.4293022330515853e-03,
         3.2384935067157478e-03, 5.8129538391935298e-03, 9.1931014024190100e-03,
         1.3429247249587217e-02, 1.8580392946885453e-02, 2.4712803576387873e-02,
         3.1898380574198262e-02, 4.0212862362522098e-02, 4.9733883778963359e-02,
         6.0538927851639349e-02, 7.2703205473310564e-02, 8.6297499958797291e-02,
         1.0138601430376767e-01, 1.1802425918529594e-01, 1.3625701935082271e-01,
         1.5611643503756842e-01, 1.7762023346394817e-01, 2.0077014326253051e-01,
         2.2555052201406356e-01, 2.5192722383607768e-01, 2.7984673032755741e-01,
         3.0923556413018516e-01, 3.4000000000000014e-01, 3.7202608365949852e-01,
         4.0517996389186173e-01, 4.3930853842180234e-01, 4.7424040917891841e-01,
         5.0978713763747807e-01, 5.4574478614862609e-01, 5.8189572660264122e-01,
         6.1801069345253812e-01, 6.5385105416429268e-01, 6.8917126659624084e-01,
         7.2372148970748695e-01, 7.5725031140199939e-01, 7.8950755527305094e-01,
         8.2024712655475274e-01, 8.4922985673746942e-01, 8.7622630607621343e-01,
         9.0101948362025164e-01, 9.2340744541290509e-01, 9.4320573313783873e-01,
         9.6024961769757267e-01, 9.7439611496782463e-01, 9.8552574423540451e-01,
         9.9354400354752948e-01, 9.9838254031929408e-01, 9.9999999999999989e-01,
         9.9838254031929408e-01, 9.9354400354752936e-01, 9.8552574423540440e-01,
         9.7439611496782452e-01, 9.6024961769757256e-01, 9.4320573313783851e-01,
         9.2340744541290487e-01, 9.0101948362025142e-01, 8.7622630607621310e-01,
         8.4922985673746942e-01, 8.2024712655475229e-01, 7.8950755527305061e-01,
         7.5725031140199917e-01, 7.2372148970748673e-01, 6.8917126659624084e-01,
         6.5385105416429223e-01, 6.1801069345253778e-01, 5.8189572660264077e-01,
         5.4574478614862576e-01, 5.0978713763747785e-01, 4.7424040917891802e-01,
         4.3930853842180212e-01, 4.0517996389186128e-01, 3.7202608365949830e-01,
         3.4000000000000002e-01, 3.0923556413018483e-01, 2.7984673032755730e-01,
         2.5192722383607730e-01, 2.2555052201406339e-01, 2.0077014326253051e-01,
         1.7762023346394792e-01, 1.5611643503756842e-01, 1.3625701935082246e-01,
         1.1802425918529583e-01, 1.0138601430376747e-01, 8.6297499958797097e-02,
         7.2703205473310564e-02, 6.0538927851639154e-02, 4.9733883778963262e-02,
         4.0212862362521952e-02, 3.1898380574198214e-02, 2.4712803576387873e-02,
         1.8580392946885335e-02, 1.3429247249587210e-02, 9.1931014024189267e-03,
         5.8129538391935159e-03, 3.2384935067157478e-03, 1.4293022330515576e-03,
         3.5581189102243393e-04, -1.3877787807814457e-17]

    ]]],

    ['Hamming', [DataWindow.createHammingWindow, [

        [],
        [.08],
        [.08, .08],
        [.08, 1, .08],
        [.08, .77, .77, .08],
        [.08, .54, 1, .54, .08],

        // size 100, from scipy.signal.get_window
        [8.0000000000000016e-02, 8.0926128822933208e-02, 8.3700786097834157e-02,
         8.8312799259154973e-02, 9.4743597357676124e-02, 1.0296728583916515e-01,
         1.1295075081260664e-01, 1.2465379238815427e-01, 1.3802928654789892e-01,
         1.5302337489765672e-01, 1.6957568153571306e-01, 1.8761955616527021e-01,
         2.0708234247166774e-01, 2.2788567068371929e-01, 2.4994577314111982e-01,
         2.7317382159724890e-01, 2.9747628489916889e-01, 3.2275530560456600e-01,
         3.4890909401913228e-01, 3.7583233806773902e-01, 4.0341662734899364e-01,
         4.3155088966566352e-01, 4.6012183827321207e-01, 4.8901442804553497e-01,
         5.1811231872107866e-01, 5.4729834336401184e-01, 5.7645498015412278e-01,
         6.0546482560571135e-01, 6.3421106730998789e-01, 6.6257795429741617e-01,
         6.9045126312601401e-01, 7.1771875781883931e-01, 7.4427064179865621e-01,
         7.7000000000000024e-01, 7.9480322937841086e-01, 8.1858045608332686e-01,
         8.4123593761483129e-01, 8.6267844834490792e-01, 8.8282164685084719e-01,
         9.0158442358168234e-01, 9.1889122745772311e-01, 9.3467237008808957e-01,
         9.4886430638126484e-01, 9.6140989041875213e-01, 9.7225860556151789e-01,
         9.8136676786266896e-01, 9.8869770196728735e-01, 9.9422188879114148e-01,
         9.9791708438361892e-01, 9.9976840949626522e-01, 9.9976840949626522e-01,
         9.9791708438361892e-01, 9.9422188879114137e-01, 9.8869770196728735e-01,
         9.8136676786266874e-01, 9.7225860556151789e-01, 9.6140989041875202e-01,
         9.4886430638126484e-01, 9.3467237008808945e-01, 9.1889122745772311e-01,
         9.0158442358168223e-01, 8.8282164685084719e-01, 8.6267844834490770e-01,
         8.4123593761483129e-01, 8.1858045608332675e-01, 7.9480322937841086e-01,
         7.6999999999999980e-01, 7.4427064179865599e-01, 7.1771875781883920e-01,
         6.9045126312601401e-01, 6.6257795429741595e-01, 6.3421106730998766e-01,
         6.0546482560571113e-01, 5.7645498015412278e-01, 5.4729834336401151e-01,
         5.1811231872107844e-01, 4.8901442804553497e-01, 4.6012183827321218e-01,
         4.3155088966566335e-01, 4.0341662734899353e-01, 3.7583233806773902e-01,
         3.4890909401913206e-01, 3.2275530560456589e-01, 2.9747628489916889e-01,
         2.7317382159724890e-01, 2.4994577314111949e-01, 2.2788567068371912e-01,
         2.0708234247166774e-01, 1.8761955616527021e-01, 1.6957568153571295e-01,
         1.5302337489765661e-01, 1.3802928654789892e-01, 1.2465379238815427e-01,
         1.1295075081260653e-01, 1.0296728583916509e-01, 9.4743597357676124e-02,
         8.8312799259154862e-02, 8.3700786097834157e-02, 8.0926128822933152e-02,
         8.0000000000000016e-02],

         // size 101, from scipy.signal.get_window
         [8.0000000000000016e-02, 8.0907704922995094e-02, 8.3627237395340226e-02,
          8.8147864664803177e-02, 9.4451745880829718e-02, 1.0251400250422937e-01,
          1.1230281649140439e-01, 1.2377955586563111e-01, 1.3689892717982272e-01,
          1.5160915426907307e-01, 1.6785218258752427e-01, 1.8556390832313702e-01,
          2.0467443138615082e-01, 2.2510833127280322e-01, 2.4678496471560296e-01,
          2.6961878394546246e-01, 2.9351967430966164e-01, 3.1839330991321113e-01,
          3.4414152588006652e-01, 3.7066270576504823e-01, 3.9785218258752425e-01,
          4.2560265190416691e-01, 4.5380459529056683e-01, 4.8234671256042011e-01,
          5.1111636101651592e-01, 5.4000000000000015e-01, 5.6888363898348426e-01,
          5.9765328743958013e-01, 6.2619540470943347e-01, 6.5439734809583328e-01,
          6.8214781741247599e-01, 7.0933729423495195e-01, 7.3585847411993355e-01,
          7.6160669008678927e-01, 7.8648032569033866e-01, 8.1038121605453772e-01,
          8.3321503528439744e-01, 8.5489166872719691e-01, 8.7532556861384947e-01,
          8.9443609167686322e-01, 9.1214781741247586e-01, 9.2839084573092712e-01,
          9.4310107282017741e-01, 9.5622044413436913e-01, 9.6769718350859579e-01,
          9.7748599749577081e-01, 9.8554825411917046e-01, 9.9185213533519689e-01,
          9.9637276260465990e-01, 9.9909229507700492e-01, 1.0000000000000000e+00,
          9.9909229507700492e-01, 9.9637276260465990e-01, 9.9185213533519678e-01,
          9.8554825411917035e-01, 9.7748599749577059e-01, 9.6769718350859568e-01,
          9.5622044413436902e-01, 9.4310107282017719e-01, 9.2839084573092689e-01,
          9.1214781741247575e-01, 8.9443609167686300e-01, 8.7532556861384925e-01,
          8.5489166872719680e-01, 8.3321503528439722e-01, 8.1038121605453772e-01,
          7.8648032569033832e-01, 7.6160669008678905e-01, 7.3585847411993321e-01,
          7.0933729423495173e-01, 6.8214781741247588e-01, 6.5439734809583305e-01,
          6.2619540470943336e-01, 5.9765328743957968e-01, 5.6888363898348404e-01,
          5.4000000000000004e-01, 5.1111636101651570e-01, 4.8234671256042000e-01,
          4.5380459529056638e-01, 4.2560265190416668e-01, 3.9785218258752425e-01,
          3.7066270576504801e-01, 3.4414152588006652e-01, 3.1839330991321080e-01,
          2.9351967430966153e-01, 2.6961878394546213e-01, 2.4678496471560263e-01,
          2.2510833127280322e-01, 2.0467443138615049e-01, 1.8556390832313685e-01,
          1.6785218258752399e-01, 1.5160915426907295e-01, 1.3689892717982272e-01,
          1.2377955586563089e-01, 1.1230281649140433e-01, 1.0251400250422926e-01,
          9.4451745880829663e-02, 8.8147864664803177e-02, 8.3627237395340170e-02,
          8.0907704922995094e-02, 8.0000000000000016e-02]

    ]]],

    ['Hann', [DataWindow.createHannWindow, [

        [],
        [0],
        [0, 0],
        [0, 1, 0],
        [0, .75, .75, 0],
        [0, .5, 1, .5, 0],

        // size 100, from scipy.signal.get_window
        [0.0000000000000000e+00, 1.0066617640578368e-03, 4.0225935846023297e-03,
         9.0356513686467022e-03, 1.6025649301821876e-02, 2.4964441129527337e-02,
         3.5816033491963717e-02, 4.8536730856689414e-02, 6.3075311465107531e-02,
         7.9373233584409453e-02, 9.7364871234470685e-02, 1.1697777844051105e-01,
         1.3813298094746490e-01, 1.6074529422143397e-01, 1.8472366645773891e-01,
         2.0997154521440098e-01, 2.3638726619474876e-01, 2.6386446261365870e-01,
         2.9229249349905684e-01, 3.2155688920406411e-01, 3.5153981233586262e-01,
         3.8212053224528642e-01, 4.1317591116653485e-01, 4.4458090004949452e-01,
         4.7620904208812898e-01, 5.0793298191740410e-01, 5.3962497842839430e-01,
         5.7115741913664264e-01, 6.0240333403259538e-01, 6.3323690684501754e-01,
         6.6353398165871091e-01, 6.9317256284656437e-01, 7.2203330630288709e-01,
         7.5000000000000022e-01, 7.7696003193305518e-01, 8.0280484356883353e-01,
         8.2743036697264261e-01, 8.5073744385316075e-01, 8.7263222483787739e-01,
         8.9302654737139386e-01, 9.1183829071491640e-01, 9.2899170661748864e-01,
         9.4441772432746174e-01, 9.5805422871603485e-01, 9.6984631039295421e-01,
         9.7974648680724874e-01, 9.8771489344270358e-01, 9.9371944433819714e-01,
         9.9773596128654229e-01, 9.9974827119159260e-01, 9.9974827119159260e-01,
         9.9773596128654229e-01, 9.9371944433819714e-01, 9.8771489344270358e-01,
         9.7974648680724863e-01, 9.6984631039295421e-01, 9.5805422871603474e-01,
         9.4441772432746174e-01, 9.2899170661748842e-01, 9.1183829071491640e-01,
         8.9302654737139364e-01, 8.7263222483787739e-01, 8.5073744385316052e-01,
         8.2743036697264261e-01, 8.0280484356883330e-01, 7.7696003193305518e-01,
         7.4999999999999978e-01, 7.2203330630288698e-01, 6.9317256284656426e-01,
         6.6353398165871091e-01, 6.3323690684501721e-01, 6.0240333403259516e-01,
         5.7115741913664253e-01, 5.3962497842839430e-01, 5.0793298191740377e-01,
         4.7620904208812875e-01, 4.4458090004949452e-01, 4.1317591116653496e-01,
         3.8212053224528619e-01, 3.5153981233586251e-01, 3.2155688920406411e-01,
         2.9229249349905650e-01, 2.6386446261365848e-01, 2.3638726619474876e-01,
         2.0997154521440098e-01, 1.8472366645773858e-01, 1.6074529422143380e-01,
         1.3813298094746490e-01, 1.1697777844051105e-01, 9.7364871234470574e-02,
         7.9373233584409342e-02, 6.3075311465107531e-02, 4.8536730856689414e-02,
         3.5816033491963606e-02, 2.4964441129527282e-02, 1.6025649301821876e-02,
         9.0356513686465911e-03, 4.0225935846023297e-03, 1.0066617640577813e-03,
         0.0000000000000000e+00],

        // length 101, from scipy.signal.get_window
        [0.0000000000000000e+00, 9.8663578586422052e-04, 3.9426493427611176e-03,
         8.8563746356556394e-03, 1.5708419435684462e-02, 2.4471741852423234e-02,
         3.5111757055874326e-02, 4.7586473766990323e-02, 6.1846659978068153e-02,
         7.7836037248992462e-02, 9.5491502812526330e-02, 1.1474337861210543e-01,
         1.3551568628929433e-01, 1.5772644703565564e-01, 1.8128800512565535e-01,
         2.0610737385376349e-01, 2.3208660251050178e-01, 2.5912316294914250e-01,
         2.8711035421746361e-01, 3.1593772365766115e-01, 3.4549150281252633e-01,
         3.7565505641757269e-01, 4.0630934270713781e-01, 4.3733338321784793e-01,
         4.6860474023534343e-01, 5.0000000000000011e-01, 5.3139525976465674e-01,
         5.6266661678215224e-01, 5.9369065729286241e-01, 6.2434494358242754e-01,
         6.5450849718747384e-01, 6.8406227634233907e-01, 7.1288964578253644e-01,
         7.4087683705085783e-01, 7.6791339748949849e-01, 7.9389262614623668e-01,
         8.1871199487434487e-01, 8.4227355296434436e-01, 8.6448431371070589e-01,
         8.8525662138789474e-01, 9.0450849718747373e-01, 9.2216396275100765e-01,
         9.3815334002193185e-01, 9.5241352623300979e-01, 9.6488824294412578e-01,
         9.7552825814757682e-01, 9.8429158056431554e-01, 9.9114362536434442e-01,
         9.9605735065723899e-01, 9.9901336421413578e-01, 1.0000000000000000e+00,
         9.9901336421413578e-01, 9.9605735065723888e-01, 9.9114362536434431e-01,
         9.8429158056431554e-01, 9.7552825814757671e-01, 9.6488824294412567e-01,
         9.5241352623300979e-01, 9.3815334002193174e-01, 9.2216396275100743e-01,
         9.0450849718747361e-01, 8.8525662138789452e-01, 8.6448431371070567e-01,
         8.4227355296434425e-01, 8.1871199487434476e-01, 7.9389262614623668e-01,
         7.6791339748949805e-01, 7.4087683705085761e-01, 7.1288964578253600e-01,
         6.8406227634233885e-01, 6.5450849718747373e-01, 6.2434494358242720e-01,
         5.9369065729286230e-01, 5.6266661678215180e-01, 5.3139525976465651e-01,
         5.0000000000000000e-01, 4.6860474023534310e-01, 4.3733338321784782e-01,
         4.0630934270713737e-01, 3.7565505641757246e-01, 3.4549150281252633e-01,
         3.1593772365766082e-01, 2.8711035421746361e-01, 2.5912316294914212e-01,
         2.3208660251050162e-01, 2.0610737385376315e-01, 1.8128800512565502e-01,
         1.5772644703565564e-01, 1.3551568628929400e-01, 1.1474337861210526e-01,
         9.5491502812526052e-02, 7.7836037248992351e-02, 6.1846659978068153e-02,
         4.7586473766990101e-02, 3.5111757055874271e-02, 2.4471741852423068e-02,
         1.5708419435684406e-02, 8.8563746356556394e-03, 3.9426493427610620e-03,
         9.8663578586422052e-04, 0.0000000000000000e+00]

    ]]],

    ['Nuttall', [DataWindow.createNuttallWindow, [

        [],
        [.0003628],
        [.0003628, .0003628],
        [.0003628, 1, .0003628],
        [.0003628, .5292298, .5292298, .0003628],
        [.0003628, .2269824, 1, .2269824, .0003628],

        // size 100, from scipy.signal.get_window
        [3.6280000000003809e-04, 4.4100256501290042e-04, 6.8237717083790596e-04,
         1.1072071925914643e-03, 1.7492358328481785e-03, 2.6555567644544606e-03,
         3.8864304903093311e-03, 5.5149979560592298e-03, 7.6268576868341242e-03,
         1.0319469437575945e-02, 1.3701346310712331e-02, 1.7890998671380040e-02,
         2.3015597041407512e-02, 2.9209327432819628e-02, 3.6611421135571975e-02,
         4.5363851544586317e-02, 5.5608702844613458e-02, 6.7485228831599756e-02,
         8.1126634332239989e-02, 9.6656626036440804e-02, 1.1418579349929589e-01,
         1.3380789401228413e-01, 1.5559612641629050e-01, 1.7959948819872706e-01,
         2.0583931691015922e-01, 2.3430612065805795e-01, 2.6495680288791129e-01,
         2.9771238365532210e-01, 3.3245631305602980e-01, 3.6903346246728608e-01,
         4.0724986594218082e-01, 4.4687326778849357e-01, 4.8763451346935727e-01,
         5.2922980000000031e-01, 5.7132377958430358e-01, 6.1355348700461687e-01,
         6.5553303796059825e-01, 6.9685902288122648e-01, 7.3711649943820157e-01,
         7.7588546776980583e-01, 8.1274769593008156e-01, 8.4729374988169215e-01,
         8.7913007292891465e-01, 9.0788595420393170e-01, 9.3322022491232959e-01,
         9.5482752461426412e-01, 9.7244398782728703e-01, 9.8585221350603325e-01,
         9.9488539616776150e-01, 9.9943051714966413e-01, 9.9943051714966413e-01,
         9.9488539616776150e-01, 9.8585221350603292e-01, 9.7244398782728703e-01,
         9.5482752461426379e-01, 9.3322022491232959e-01, 9.0788595420393159e-01,
         8.7913007292891465e-01, 8.4729374988169193e-01, 8.1274769593008156e-01,
         7.7588546776980549e-01, 7.3711649943820157e-01, 6.9685902288122625e-01,
         6.5553303796059825e-01, 6.1355348700461665e-01, 5.7132377958430358e-01,
         5.2922979999999975e-01, 4.8763451346935693e-01, 4.4687326778849346e-01,
         4.0724986594218082e-01, 3.6903346246728569e-01, 3.3245631305602963e-01,
         2.9771238365532204e-01, 2.6495680288791129e-01, 2.3430612065805764e-01,
         2.0583931691015900e-01, 1.7959948819872706e-01, 1.5559612641629056e-01,
         1.3380789401228399e-01, 1.1418579349929583e-01, 9.6656626036440804e-02,
         8.1126634332239850e-02, 6.7485228831599686e-02, 5.5608702844613458e-02,
         4.5363851544586317e-02, 3.6611421135571871e-02, 2.9209327432819576e-02,
         2.3015597041407512e-02, 1.7890998671380040e-02, 1.3701346310712313e-02,
         1.0319469437575928e-02, 7.6268576868341242e-03, 5.5149979560592298e-03,
         3.8864304903093033e-03, 2.6555567644544588e-03, 1.7492358328481785e-03,
         1.1072071925914279e-03, 6.8237717083792677e-04, 4.4100256501283970e-04,
         3.6280000000003809e-04],

        // size 101, from scipy.signal.get_window
        [3.6280000000003809e-04, 4.3943533275720911e-04, 6.7584165234204144e-04,
         1.0915036026995974e-03, 1.7188369763968692e-03, 2.6030862749787803e-03,
         3.8021530763779343e-03, 5.3863288716700193e-03, 7.4379011062129909e-03,
         1.0050598032562329e-02, 1.3328836896113092e-02, 1.7386741085282861e-02,
         2.2346895249321715e-02, 2.8338812984825948e-02, 3.5497099385972515e-02,
         4.3959300319126524e-02, 5.3863441409176309e-02, 6.5345272026252885e-02,
         7.8535242588636367e-02, 9.3555256755636085e-02, 1.1051525304987182e-01,
         1.2950968258966034e-01, 1.5061396040820060e-01, 1.7388097679708006e-01,
         1.9933776179738055e-01, 2.2698240000000011e-01, 2.5678129391820559e-01,
         2.8866687216573916e-01, 3.2253583342361525e-01, 3.5824800872903628e-01,
         3.9562591310388706e-01, 4.3445504320146194e-01, 4.7448496083601144e-01,
         5.1543118341228056e-01, 5.5697788191453779e-01, 5.9878136583463226e-01,
         6.4047431285052236e-01, 6.8167067987028529e-01, 7.2197121189556734e-01,
         7.6096944667822275e-01, 7.9825809695012828e-01, 8.3343567864372392e-01,
         8.6611324345525398e-01, 8.9592106770368241e-01, 9.2251514696652437e-01,
         9.4558334757126272e-01, 9.6485107170490669e-01, 9.8008630256548490e-01,
         9.9110390938483894e-01, 9.9776910895165682e-01, 1.0000000000000000e+00,
         9.9776910895165682e-01, 9.9110390938483883e-01, 9.8008630256548479e-01,
         9.6485107170490658e-01, 9.4558334757126239e-01, 9.2251514696652415e-01,
         8.9592106770368229e-01, 8.6611324345525376e-01, 8.3343567864372370e-01,
         7.9825809695012806e-01, 7.6096944667822231e-01, 7.2197121189556701e-01,
         6.8167067987028518e-01, 6.4047431285052203e-01, 5.9878136583463226e-01,
         5.5697788191453712e-01, 5.1543118341228022e-01, 4.7448496083601088e-01,
         4.3445504320146161e-01, 3.9562591310388689e-01, 3.5824800872903600e-01,
         3.2253583342361514e-01, 2.8866687216573877e-01, 2.5678129391820537e-01,
         2.2698240000000006e-01, 1.9933776179738022e-01, 1.7388097679708001e-01,
         1.5061396040820030e-01, 1.2950968258966020e-01, 1.1051525304987182e-01,
         9.3555256755635904e-02, 7.8535242588636367e-02, 6.5345272026252732e-02,
         5.3863441409176240e-02, 4.3959300319126413e-02, 3.5497099385972404e-02,
         2.8338812984825948e-02, 2.2346895249321656e-02, 1.7386741085282795e-02,
         1.3328836896113022e-02, 1.0050598032562313e-02, 7.4379011062129909e-03,
         5.3863288716699594e-03, 3.8021530763779456e-03, 2.6030862749787369e-03,
         1.7188369763968692e-03, 1.0915036026995974e-03, 6.7584165234202756e-04,
         4.3943533275720564e-04, 3.6280000000003809e-04]

    ]]],

    ['Rectangular', [DataWindow.createRectangularWindow, [
        [],
        [1],
        [1, 1],
        [1, 1, 1],
        [1, 1, 1, 1],
        [1, 1, 1, 1, 1]
    ]]]

]);


function _testWindow(name) {
    const [windowFunction, expectedWindows] = _TEST_CASES.get(name);
    _testWindowFunction(windowFunction, expectedWindows);
}


function _testWindowFunction(windowFunction, expectedWindows) {

    for (const expectedWindow of expectedWindows) {

        const size = expectedWindow.length;

        // default `symmetric` argument (`true`)
        let window = windowFunction(size);
        expect(window).toAlmostEqual(expectedWindow);

        // `symmetric` argument `true`
        window = windowFunction(size, true);
        expect(window).toAlmostEqual(expectedWindow);

        // `symmetric` argument `false`
        if (size !== 0) {
            window = windowFunction(size - 1, false);
            expect(window).toAlmostEqual(expectedWindow.slice(0, size - 1));
        }

    }

}


function _createWindowFunction(name) {
    return function(size, symmetric = true) {
        return DataWindow.createWindow(name, size, symmetric);
    }
}


describe('DataWindow', () => {

    beforeEach(() => addAlmostEqualMatcher());

    for (const windowName of _TEST_CASES.keys()) {
        it(`create${windowName}Window`, () => {
            _testWindow(windowName);
        })
    }

    it('createWindow', () => {
        for (const [name, [_, expectedWindows]] of _TEST_CASES) {
            const windowFunction = _createWindowFunction(name);
            _testWindowFunction(windowFunction, expectedWindows);
        }
    });

    it('createWindow errors', () => {
        expect(() => DataWindow.createWindow('Hann', -1)).toThrowError(Error);
        expect(() => DataWindow.createWindow('Hann', .5)).toThrowError(Error);
    });

});
